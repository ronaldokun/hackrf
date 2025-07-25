function hackrf_udp_client(action, varargin)
%HACKRF_UDP_CLIENT MATLAB client for HackRF UDP server
%
% This function provides a complete MATLAB interface to the HackRF UDP server,
% allowing you to perform spectrum analysis and data collection directly
% from MATLAB/Simulink applications.
%
% USAGE:
%   hackrf_udp_client('demo')              - Run interactive demo
%   hackrf_udp_client('fm_scan')           - Quick FM radio scan
%   hackrf_udp_client('custom_scan', args) - Custom frequency scan
%   hackrf_udp_client('test_connection')   - Test server connection
%   hackrf_udp_client('server_stats')      - Get server statistics
%
% EXAMPLES:
%   % Quick FM radio scan
%   data = hackrf_udp_client('fm_scan');
%   
%   % Custom frequency scan
%   args = {'-f', '400:450', '-g', '30', '-l', '24', '-w', '1000000'};
%   data = hackrf_udp_client('custom_scan', args, 'duration', 15);
%   
%   % Interactive demo with plots
%   hackrf_udp_client('demo');
%
% PARAMETERS:
%   'server'     - Server address (default: 'localhost')
%   'port'       - Server port (default: 5000)
%   'duration'   - Scan duration in seconds (default: 10)
%   'plot'       - Generate plots (default: true)
%   'save_data'  - Save data to .mat file (default: false)
%
% RETURNS:
%   Structure with fields:
%     .data          - Raw HackRF data lines
%     .timestamps    - Parsed timestamps
%     .frequencies   - Frequency data
%     .power_levels  - Power level measurements
%     .metadata      - Scan metadata
%
% REQUIREMENTS:
%   - MATLAB R2019b or later (for UDP support)
%   - Instrument Control Toolbox (recommended)
%   - Signal Processing Toolbox (for analysis functions)
%
% AUTHOR: Claude Sonnet 4 with a little nudge from Ronaldo da Silva Alves Batista
% DATE: 2025-07-25

    if nargin < 1
        action = 'demo';
    end
    
    % Parse input arguments
    p = inputParser;
    addParameter(p, 'server', 'localhost', @ischar);
    addParameter(p, 'port', 5000, @isnumeric);
    addParameter(p, 'duration', 10, @isnumeric);
    addParameter(p, 'plot', true, @islogical);
    addParameter(p, 'save_data', false, @islogical);
    addParameter(p, 'verbose', true, @islogical);
    parse(p, varargin{:});
    
    params = p.Results;
    
    % Execute requested action
    switch lower(action)
        case 'demo'
            run_interactive_demo(params);
        case 'fm_scan'
            result = perform_fm_scan(params);
            if nargout > 0
                varargout{1} = result;
            end
        case 'custom_scan'
            if length(varargin) >= 1 && iscell(varargin{1})
                hackrf_args = varargin{1};
                custom_params = parse_custom_params(varargin(2:end));
                params = merge_params(params, custom_params);
            else
                error('custom_scan requires hackrf_sweep arguments as first parameter');
            end
            result = perform_custom_scan(hackrf_args, params);
            if nargout > 0
                varargout{1} = result;
            end
        case 'test_connection'
            test_server_connection(params);
        case 'server_stats'
            stats = get_server_stats(params);
            if nargout > 0
                varargout{1} = stats;
            else
                display_server_stats(stats);
            end
        otherwise
            error('Unknown action: %s', action);
    end
end

function run_interactive_demo(params)
%RUN_INTERACTIVE_DEMO Interactive demonstration of HackRF UDP client capabilities
    
    fprintf('\n🎵 HackRF UDP Client - MATLAB Demo\n');
    fprintf('=====================================\n\n');
    
    % Test connection first
    fprintf('📡 Testing connection to server...\n');
    if ~test_server_connection(params)
        fprintf('❌ Cannot connect to server. Please check:\n');
        fprintf('   - Server is running: python3 hackrf_udp_server.py\n');
        fprintf('   - Server address: %s:%d\n', params.server, params.port);
        return;
    end
    
    fprintf('✅ Server connection successful!\n\n');
    
    % Show server statistics
    fprintf('📊 Server Statistics:\n');
    stats = get_server_stats(params);
    display_server_stats(stats);
    
    % Interactive menu
    while true
        fprintf('\n🎛️  Available Actions:\n');
        fprintf('1. FM Radio Band Scan (88-108 MHz)\n');
        fprintf('2. Custom Frequency Scan\n');
        fprintf('3. Wide Spectrum Survey\n');
        fprintf('4. Server Statistics\n');
        fprintf('5. Exit Demo\n\n');
        
        choice = input('Select an option (1-5): ');
        
        switch choice
            case 1
                fprintf('\n🎵 Starting FM Radio Band Scan...\n');
                data = perform_fm_scan(params);
                if params.plot
                    plot_fm_spectrum(data);
                end
                
            case 2
                fprintf('\n📻 Custom Frequency Scan Setup:\n');
                freq_range = input('Frequency range (MHz, e.g., "400:450"): ', 's');
                gain = input('VGA gain (0-62, default 20): ');
                if isempty(gain), gain = 20; end
                lna_gain = input('LNA gain (0-40, default 16): ');
                if isempty(lna_gain), lna_gain = 16; end
                duration = input('Duration (seconds, default 10): ');
                if isempty(duration), duration = 10; end
                
                args = {'-f', freq_range, '-g', num2str(gain), '-l', num2str(lna_gain), '-w', '1000000'};
                custom_params = params;
                custom_params.duration = duration;
                
                fprintf('\n📡 Starting custom scan: %s MHz...\n', freq_range);
                data = perform_custom_scan(args, custom_params);
                if params.plot
                    plot_spectrum_data(data);
                end
                
            case 3
                fprintf('\n🌐 Wide Spectrum Survey (100-1000 MHz)...\n');
                args = {'-f', '100:1000', '-g', '30', '-l', '24', '-w', '2000000'};
                wide_params = params;
                wide_params.duration = 30;
                
                data = perform_custom_scan(args, wide_params);
                if params.plot
                    plot_wide_spectrum(data);
                end
                
            case 4
                fprintf('\n📊 Current Server Statistics:\n');
                stats = get_server_stats(params);
                display_server_stats(stats);
                
            case 5
                fprintf('\n👋 Exiting demo. Happy spectrum analyzing!\n');
                break;
                
            otherwise
                fprintf('❌ Invalid choice. Please select 1-5.\n');
        end
    end
end

function result = perform_fm_scan(params)
%PERFORM_FM_SCAN Perform FM radio band scan (88-108 MHz)
    
    if params.verbose
        fprintf('🎵 Starting FM radio band scan...\n');
        fprintf('   Frequency: 88-108 MHz\n');
        fprintf('   Duration: %d seconds\n', params.duration);
    end
    
    % HackRF arguments for FM band
    hackrf_args = {'-f', '88:108', '-g', '20', '-l', '16', '-w', '1000000'};
    
    % Perform the scan
    result = perform_hackrf_scan(hackrf_args, params);
    result.scan_type = 'FM Radio Band';
    result.frequency_range = [88, 108]; % MHz
    
    if params.verbose
        fprintf('✅ FM scan completed: %d data points collected\n', length(result.data));
    end
end

function result = perform_custom_scan(hackrf_args, params)
%PERFORM_CUSTOM_SCAN Perform custom frequency scan with specified arguments
    
    if params.verbose
        fprintf('📻 Starting custom frequency scan...\n');
        fprintf('   Arguments: %s\n', strjoin(hackrf_args, ' '));
        fprintf('   Duration: %d seconds\n', params.duration);
    end
    
    % Perform the scan
    result = perform_hackrf_scan(hackrf_args, params);
    result.scan_type = 'Custom Frequency Scan';
    
    % Try to extract frequency range from arguments
    freq_idx = find(strcmp(hackrf_args, '-f'));
    if ~isempty(freq_idx) && length(hackrf_args) > freq_idx
        freq_range_str = hackrf_args{freq_idx + 1};
        if contains(freq_range_str, ':')
            freq_parts = split(freq_range_str, ':');
            result.frequency_range = [str2double(freq_parts{1}), str2double(freq_parts{2})];
        end
    end
    
    if params.verbose
        fprintf('✅ Custom scan completed: %d data points collected\n', length(result.data));
    end
end

function result = perform_hackrf_scan(hackrf_args, params)
%PERFORM_HACKRF_SCAN Core function to perform HackRF spectrum scan
    
    % Create UDP connection
    try
        udp_client = udpport("LocalHost", "0.0.0.0", "LocalPort", 0);
        server_addr = params.server;
        server_port = params.port;
    catch ME
        error('Failed to create UDP client: %s', ME.message);
    end
    
    try
        % Step 1: Connect to server
        if params.verbose
            fprintf('📡 Connecting to HackRF server...\n');
        end
        
        write(udp_client, uint8('CONNECT'), server_addr, server_port);
        pause(0.1); % Small delay for response
        
        % Read connection response
        if udp_client.NumBytesAvailable > 0
            connect_data = read(udp_client, udp_client.NumBytesAvailable, "uint8");
            connect_response = char(connect_data');
            if params.verbose && contains(connect_response, 'connected')
                fprintf('✅ Connected to server\n');
            end
        else
            error('No response from server during connection');
        end
        
        % Step 2: Start stream
        if params.verbose
            fprintf('🚀 Starting data stream...\n');
        end
        
        % Build START_STREAM command
        args_json = jsonencode(struct('args', {hackrf_args}));
        start_command = sprintf('START_STREAM %s', args_json);
        
        write(udp_client, uint8(start_command), server_addr, server_port);
        pause(0.1);
        
        % Read start response
        if udp_client.NumBytesAvailable > 0
            start_data = read(udp_client, udp_client.NumBytesAvailable, "uint8");
            start_response = char(start_data');
            if ~contains(start_response, 'stream_started')
                error('Failed to start stream: %s', start_response);
            end
        end
        
        % Step 3: Collect streaming data
        if params.verbose
            fprintf('📊 Collecting data for %d seconds...\n', params.duration);
        end
        
        data_lines = {};
        start_time = tic;
        last_update = 0;
        
        while toc(start_time) < params.duration
            if udp_client.NumBytesAvailable > 0
                % Read available data
                raw_data = read(udp_client, udp_client.NumBytesAvailable, "uint8");
                data_str = char(raw_data');
                
                % Split into lines and filter
                lines = strsplit(data_str, '\n');
                for i = 1:length(lines)
                    line = strtrim(lines{i});
                    % Keep lines that look like HackRF data (contain commas, not JSON)
                    if ~isempty(line) && ~startsWith(line, '{') && contains(line, ',')
                        data_lines{end+1} = line; %#ok<AGROW>
                    end
                end
                
                % Progress update every 2 seconds
                if params.verbose && toc(start_time) - last_update > 2
                    fprintf('   Collected %d lines so far...\n', length(data_lines));
                    last_update = toc(start_time);
                end
            else
                pause(0.1); % Small delay when no data available
            end
        end
        
        % Step 4: Stop stream
        if params.verbose
            fprintf('⏹️  Stopping stream...\n');
        end
        
        write(udp_client, uint8('STOP_STREAM'), server_addr, server_port);
        pause(0.1);
        if udp_client.NumBytesAvailable > 0
            read(udp_client, udp_client.NumBytesAvailable, "uint8"); % Clear buffer
        end
        
        % Step 5: Disconnect
        write(udp_client, uint8('DISCONNECT'), server_addr, server_port);
        pause(0.1);
        if udp_client.NumBytesAvailable > 0
            read(udp_client, udp_client.NumBytesAvailable, "uint8"); % Clear buffer
        end
        
    catch ME
        error('HackRF scan failed: %s', ME.message);
    finally
        % Clean up UDP connection
        try
            clear udp_client;
        catch
            % Ignore cleanup errors
        end
    end
    
    % Process collected data
    result = process_hackrf_data(data_lines, params);
    
    % Save data if requested
    if params.save_data
        filename = sprintf('hackrf_data_%s.mat', datestr(now, 'yyyymmdd_HHMMSS'));
        save(filename, 'result');
        if params.verbose
            fprintf('💾 Data saved to: %s\n', filename);
        end
    end
end

function result = process_hackrf_data(data_lines, params)
%PROCESS_HACKRF_DATA Parse and structure HackRF data
    
    result = struct();
    result.data = data_lines;
    result.num_samples = length(data_lines);
    result.collection_time = params.duration;
    result.data_rate = result.num_samples / params.duration;
    
    if isempty(data_lines)
        result.timestamps = [];
        result.frequencies = [];
        result.power_levels = [];
        result.metadata = struct('error', 'No data collected');
        return;
    end
    
    % Parse data lines
    timestamps = {};
    frequencies = [];
    power_data = [];
    
    for i = 1:min(length(data_lines), 1000) % Process first 1000 lines for speed
        line = data_lines{i};
        parts = strsplit(line, ',');
        
        if length(parts) >= 7
            try
                % Parse timestamp (first two fields)
                timestamps{end+1} = sprintf('%s %s', strtrim(parts{1}), strtrim(parts{2})); %#ok<AGROW>
                
                % Parse frequency data
                freq_low = str2double(strtrim(parts{3}));
                freq_high = str2double(strtrim(parts{4}));
                frequencies(end+1) = (freq_low + freq_high) / 2; %#ok<AGROW>
                
                % Parse power levels (remaining fields)
                power_values = [];
                for j = 7:length(parts)
                    val = str2double(strtrim(parts{j}));
                    if ~isnan(val)
                        power_values(end+1) = val; %#ok<AGROW>
                    end
                end
                if ~isempty(power_values)
                    power_data(end+1) = mean(power_values); %#ok<AGROW>
                else
                    power_data(end+1) = NaN; %#ok<AGROW>
                end
                
            catch
                % Skip malformed lines
                continue;
            end
        end
    end
    
    result.timestamps = timestamps;
    result.frequencies = frequencies / 1e6; % Convert to MHz
    result.power_levels = power_data;
    result.metadata = struct('parsed_lines', length(timestamps), 'total_lines', length(data_lines));
end

function success = test_server_connection(params)
%TEST_SERVER_CONNECTION Test connection to HackRF UDP server
    
    success = false;
    
    try
        % Create UDP connection
        udp_client = udpport("LocalHost", "0.0.0.0", "LocalPort", 0);
        
        % Send PING
        write(udp_client, uint8('PING'), params.server, params.port);
        pause(0.5); % Wait for response
        
        if udp_client.NumBytesAvailable > 0
            response_data = read(udp_client, udp_client.NumBytesAvailable, "uint8");
            response = char(response_data');
            success = contains(response, 'PONG');
        end
        
        clear udp_client;
        
    catch
        success = false;
    end
end

function stats = get_server_stats(params)
%GET_SERVER_STATS Get server statistics
    
    stats = struct();
    
    try
        % Create UDP connection
        udp_client = udpport("LocalHost", "0.0.0.0", "LocalPort", 0);
        
        % Send STATS command
        write(udp_client, uint8('STATS'), params.server, params.port);
        pause(0.5); % Wait for response
        
        if udp_client.NumBytesAvailable > 0
            response_data = read(udp_client, udp_client.NumBytesAvailable, "uint8");
            response = char(response_data');
            
            try
                stats = jsondecode(response);
            catch
                stats.raw_response = response;
            end
        end
        
        clear udp_client;
        
    catch ME
        stats.error = ME.message;
    end
end

function display_server_stats(stats)
%DISPLAY_SERVER_STATS Display server statistics in a formatted way
    
    if isfield(stats, 'error')
        fprintf('❌ Error getting stats: %s\n', stats.error);
        return;
    end
    
    if isfield(stats, 'total_clients')
        fprintf('   Total Clients: %d\n', stats.total_clients);
    end
    
    if isfield(stats, 'active_processes')
        fprintf('   Active Processes: %d\n', stats.active_processes);
    end
    
    if isfield(stats, 'server_running')
        fprintf('   Server Running: %s\n', logical2str(stats.server_running));
    end
    
    if isfield(stats, 'clients') && ~isempty(stats.clients)
        fprintf('   Connected Clients:\n');
        for i = 1:length(stats.clients)
            client = stats.clients(i);
            fprintf('     - %s (%.1f min ago)\n', client.address, client.duration/60);
        end
    end
end

function plot_fm_spectrum(data)
%PLOT_FM_SPECTRUM Plot FM radio spectrum analysis
    
    if isempty(data.frequencies) || isempty(data.power_levels)
        fprintf('⚠️  No frequency data available for plotting\n');
        return;
    end
    
    figure('Name', 'FM Radio Spectrum Analysis', 'Position', [100, 100, 1000, 600]);
    
    % Subplot 1: Power vs Frequency
    subplot(2, 1, 1);
    scatter(data.frequencies, data.power_levels, 10, 'filled');
    xlabel('Frequency (MHz)');
    ylabel('Power Level (dB)');
    title(sprintf('FM Radio Band Spectrum (88-108 MHz) - %d samples', length(data.power_levels)));
    grid on;
    xlim([88, 108]);
    
    % Subplot 2: Power histogram
    subplot(2, 1, 2);
    histogram(data.power_levels, 50);
    xlabel('Power Level (dB)');
    ylabel('Count');
    title('Power Level Distribution');
    grid on;
    
    % Add metadata text
    annotation('textbox', [0.02, 0.02, 0.3, 0.1], 'String', ...
        sprintf('Scan Duration: %ds\nData Rate: %.1f samples/sec\nTotal Samples: %d', ...
        data.collection_time, data.data_rate, data.num_samples), ...
        'FitBoxToText', 'on', 'BackgroundColor', 'white');
end

function plot_spectrum_data(data)
%PLOT_SPECTRUM_DATA Plot general spectrum data
    
    if isempty(data.frequencies) || isempty(data.power_levels)
        fprintf('⚠️  No frequency data available for plotting\n');
        return;
    end
    
    figure('Name', 'Spectrum Analysis', 'Position', [100, 100, 1000, 400]);
    
    scatter(data.frequencies, data.power_levels, 10, 'filled');
    xlabel('Frequency (MHz)');
    ylabel('Power Level (dB)');
    
    if isfield(data, 'frequency_range') && ~isempty(data.frequency_range)
        title(sprintf('Spectrum: %.1f-%.1f MHz (%d samples)', ...
            data.frequency_range(1), data.frequency_range(2), length(data.power_levels)));
        xlim(data.frequency_range);
    else
        title(sprintf('Spectrum Analysis (%d samples)', length(data.power_levels)));
    end
    
    grid on;
    
    % Add metadata
    annotation('textbox', [0.02, 0.02, 0.3, 0.15], 'String', ...
        sprintf('Duration: %ds\nRate: %.1f samples/sec\nSamples: %d\nRange: %.1f dB', ...
        data.collection_time, data.data_rate, data.num_samples, ...
        range(data.power_levels)), ...
        'FitBoxToText', 'on', 'BackgroundColor', 'white');
end

function plot_wide_spectrum(data)
%PLOT_WIDE_SPECTRUM Plot wide spectrum survey data
    
    if isempty(data.frequencies) || isempty(data.power_levels)
        fprintf('⚠️  No frequency data available for plotting\n');
        return;
    end
    
    figure('Name', 'Wide Spectrum Survey', 'Position', [100, 100, 1200, 800]);
    
    % Subplot 1: Full spectrum
    subplot(3, 1, 1);
    plot(data.frequencies, data.power_levels, '.', 'MarkerSize', 2);
    xlabel('Frequency (MHz)');
    ylabel('Power Level (dB)');
    title('Wide Spectrum Survey (100-1000 MHz)');
    grid on;
    xlim([100, 1000]);
    
    % Subplot 2: Power distribution
    subplot(3, 1, 2);
    histogram(data.power_levels, 100);
    xlabel('Power Level (dB)');
    ylabel('Count');
    title('Power Level Distribution');
    grid on;
    
    % Subplot 3: Frequency vs Time (if enough data)
    subplot(3, 1, 3);
    if length(data.frequencies) > 100
        % Show frequency scanning pattern
        plot(1:min(1000, length(data.frequencies)), data.frequencies(1:min(1000, end)));
        xlabel('Sample Number');
        ylabel('Frequency (MHz)');
        title('Frequency Scanning Pattern');
        grid on;
    else
        text(0.5, 0.5, 'Insufficient data for time analysis', ...
            'HorizontalAlignment', 'center', 'Units', 'normalized');
    end
end

function custom_params = parse_custom_params(args)
%PARSE_CUSTOM_PARAMS Parse custom parameters from argument list
    
    custom_params = struct();
    
    i = 1;
    while i <= length(args)
        if ischar(args{i})
            switch lower(args{i})
                case 'duration'
                    if i < length(args)
                        custom_params.duration = args{i+1};
                        i = i + 2;
                    else
                        i = i + 1;
                    end
                case 'plot'
                    if i < length(args)
                        custom_params.plot = args{i+1};
                        i = i + 2;
                    else
                        i = i + 1;
                    end
                case 'save_data'
                    if i < length(args)
                        custom_params.save_data = args{i+1};
                        i = i + 2;
                    else
                        i = i + 1;
                    end
                otherwise
                    i = i + 1;
            end
        else
            i = i + 1;
        end
    end
end

function merged = merge_params(base_params, custom_params)
%MERGE_PARAMS Merge custom parameters with base parameters
    
    merged = base_params;
    fields = fieldnames(custom_params);
    
    for i = 1:length(fields)
        merged.(fields{i}) = custom_params.(fields{i});
    end
end

function str = logical2str(val)
%LOGICAL2STR Convert logical value to string
    if val
        str = 'Yes';
    else
        str = 'No';
    end
end
