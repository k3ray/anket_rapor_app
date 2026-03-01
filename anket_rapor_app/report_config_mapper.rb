#!/usr/bin/env ruby
# frozen_string_literal: true

require 'date'
require 'json'
require 'rexml/document'
require 'time'
require 'shellwords'
require 'yaml'

CONFIG_PATH = File.expand_path('config/config_rizepem_2026_2.yaml', __dir__)

module HeaderNormalization
  BOM = "\uFEFF"
  ZERO_WIDTH_REGEX = /[\u200B\u200C\u200D\u2060]/.freeze

  def self.normalize(value)
    text = value.to_s.dup
    text.gsub!(BOM, '')
    text.gsub!(ZERO_WIDTH_REGEX, '')
    text.gsub!(/&nbsp;/i, ' ')
    text.gsub!(/\s+/, ' ')
    text.strip!
    text
  end
end

class XlsxReader
  Cell = Struct.new(:ref, :value)

  def initialize(path)
    @path = path
  end

  def headers(sheet_name)
    shared_strings = parse_shared_strings
    target = sheet_target_for(sheet_name)
    first_row_cells(sheet_path_for_target(target), shared_strings)
  end

  private

  def zip_read(entry)
    content = `unzip -p #{Shellwords.escape(@path)} #{Shellwords.escape(entry)} 2>/dev/null`
    return nil if content.nil? || content.empty?

    content
  end

  def parse_xml(entry)
    content = zip_read(entry)
    return nil unless content

    REXML::Document.new(content)
  end

  def parse_shared_strings
    xml = parse_xml('xl/sharedStrings.xml')
    return [] unless xml

    strings = []
    REXML::XPath.each(xml, '//xmlns:si') do |si|
      parts = []
      si.each_element('.//xmlns:t') { |t| parts << t.text.to_s }
      strings << parts.join
    end
    strings
  end

  def sheet_target_for(sheet_name)
    workbook = parse_xml('xl/workbook.xml')
    raise "Workbook okunamadı: #{@path}" unless workbook

    rel_id = nil
    REXML::XPath.each(workbook, '//xmlns:sheet') do |sheet|
      if sheet.attributes['name'] == sheet_name
        rel_id = sheet.attributes['r:id']
        break
      end
    end
    raise "Sheet bulunamadı: #{sheet_name}" unless rel_id

    rels = parse_xml('xl/_rels/workbook.xml.rels')
    raise 'Workbook ilişkileri okunamadı' unless rels

    target = nil
    REXML::XPath.each(rels, '//xmlns:Relationship') do |rel|
      if rel.attributes['Id'] == rel_id
        target = rel.attributes['Target']
        break
      end
    end
    raise "Sheet relationship target bulunamadı: #{rel_id}" unless target

    target
  end

  def sheet_path_for_target(target)
    target.start_with?('/') ? target.sub(%r{^/}, '') : File.join('xl', target)
  end

  def first_row_cells(sheet_path, shared_strings)
    sheet_xml = parse_xml(sheet_path)
    raise "Sheet XML okunamadı: #{sheet_path}" unless sheet_xml

    row = REXML::XPath.first(sheet_xml, '//xmlns:sheetData/xmlns:row[@r="1"]')
    return [] unless row

    cells = []
    row.each_element('xmlns:c') do |cell|
      ref = cell.attributes['r']
      cell_type = cell.attributes['t']
      value = extract_cell_value(cell, cell_type, shared_strings)
      cells << Cell.new(ref, value)
    end
    cells
  end

  def extract_cell_value(cell, cell_type, shared_strings)
    if cell_type == 'inlineStr'
      return REXML::XPath.first(cell, 'xmlns:is/xmlns:t')&.text.to_s
    end

    raw = REXML::XPath.first(cell, 'xmlns:v')&.text
    return '' if raw.nil?

    return shared_strings[raw.to_i].to_s if cell_type == 's'

    raw
  end
end

class ReportConfigMapper
  def initialize(config_path: CONFIG_PATH)
    @config_path = config_path
    @warnings = []
  end

  attr_reader :warnings

  def build(input_xlsx:)
    config = YAML.load_file(@config_path)
    sheet_name = config.dig('input', 'sheet') || 'Sayfa'
    headers = XlsxReader.new(input_xlsx).headers(sheet_name)

    header_map = build_header_map(headers)
    closed_ended_columns = closed_ended_columns_from_config(config)
    closed_ended_order = excel_ordered_closed_ended(headers, closed_ended_columns)

    missing = closed_ended_columns.reject { |c| header_map.key?(c) }
    unless missing.empty?
      @warnings << "Kapalı uçlu soru kolonları eksik: #{missing.join(' | ')}"
    end

    submitted_at_aliases = Array(config.dig('fields', 'submitted_at', 'aliases')).map { |a| HeaderNormalization.normalize(a) }
    submitted_at_column = submitted_at_aliases.find { |alias_name| header_map.key?(alias_name) }
    if submitted_at_column.nil?
      @warnings << "submitted_at kolonu bulunamadı. Denenen aliaslar: #{submitted_at_aliases.join(', ')}"
    end

    {
      config_path: @config_path,
      input_xlsx: input_xlsx,
      sheet: sheet_name,
      closed_ended_order_from_excel: closed_ended_order,
      submitted_at_column: submitted_at_column,
      warnings: @warnings
    }
  end

  def format_submitted_at(raw_value)
    return nil if raw_value.nil? || raw_value.to_s.strip.empty?

    dt = parse_datetime(raw_value)
    return nil unless dt

    dt.strftime('%d.%m.%Y')
  end

  private

  def parse_datetime(raw)
    return raw.to_date if raw.respond_to?(:to_date)

    Time.parse(raw.to_s)
  rescue ArgumentError
    DateTime.parse(raw.to_s)
  rescue ArgumentError
    @warnings << "submitted_at parse edilemedi: #{raw.inspect}"
    nil
  end

  def build_header_map(headers)
    map = {}
    headers.each do |cell|
      normalized = HeaderNormalization.normalize(cell.value)
      next if normalized.empty?

      map[normalized] = cell.value
    end
    map
  end

  def closed_ended_columns_from_config(config)
    sections = Array(config['sections'])
    configured = []

    sections.each do |section|
      next unless section['type'] == 'closed_ended'

      Array(section['questions']).each do |question|
        col = question.is_a?(Hash) ? question['column'] : question
        normalized = HeaderNormalization.normalize(col)
        configured << normalized unless normalized.empty?
      end

      Array(section['post_questions']).each do |question|
        col = question['column']
        normalized = HeaderNormalization.normalize(col)
        configured << normalized unless normalized.empty?
      end
    end

    configured.uniq
  end

  def excel_ordered_closed_ended(headers, configured_normalized)
    set = configured_normalized.to_h { |c| [c, true] }
    ordered = []

    headers.each do |cell|
      normalized = HeaderNormalization.normalize(cell.value)
      next unless set[normalized]

      ordered << {
        excel_header: cell.value,
        normalized_header: normalized
      }
    end
    ordered
  end
end

if $PROGRAM_NAME == __FILE__
  require 'optparse'
  require 'shellwords'

  options = {
    config: CONFIG_PATH
  }

  OptionParser.new do |opts|
    opts.banner = 'Usage: report_config_mapper.rb --xlsx samples/input.xlsx [--submitted-at "2026-01-01 10:30"]'
    opts.on('--xlsx PATH', 'Excel dosya yolu') { |v| options[:xlsx] = v }
    opts.on('--config PATH', 'Config YAML yolu') { |v| options[:config] = v }
    opts.on('--submitted-at VALUE', 'Örnek submitted_at değeri (format testi)') { |v| options[:submitted_at] = v }
  end.parse!

  abort('Hata: --xlsx zorunlu') unless options[:xlsx]

  mapper = ReportConfigMapper.new(config_path: options[:config])
  result = mapper.build(input_xlsx: options[:xlsx])

  if options[:submitted_at]
    result[:submitted_at_formatted] = mapper.format_submitted_at(options[:submitted_at])
  end

  puts JSON.pretty_generate(result)
end
