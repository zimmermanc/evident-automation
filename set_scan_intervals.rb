require "esp_sdk"

#=== Description ===
# Updates the scan intervals for all services of specified accounts to a specified value.
#
# Instructions:
# 1. Enter your ESP API Public Key and Secret Key
# 2. Modify external_account_ids to include the list of External Accounts IDs that you want to update
# 3. Modify INTERVAL to desired interval value (in minutes).
#
#=== End Description ===

#=== Configuration ===
ESP.access_key_id = <public key>
ESP.secret_access_key = <secret key>
external_account_ids = [<account_id>, <account_id>, ...]
INTERVAL = 60 # minutes
#=== End Configuration ===

#=== Helper Methods ===
# Run ESP methods with retry
def call_esp(esp, args)
    count = 0
    retry_limit = 5
    while (count < retry_limit)
        begin
            return esp.call(*args)
        rescue ActiveResource::ClientError => e
            if (e.response.code.to_i == 429)
                # Wait 60 seconds before retry
                puts "API rate limit reached, wait #{60 * (count+1)} seconds before retry"
                sleep(60 * (count+1))
            end
        end
        count += 1
    end
    raise Exception.new("Retry too many times. Abort.")
end

# Check if script should run
# Should NOT run if authenticated user has Evident role
def proceed?()
    organizations = ESP::Organization.all

    if organizations.count != 1
        puts "Do NOT run this with Evident role user."
        Kernel.exit(true)
    end
end
#=== End Helper Methods ===

#=== Main Script ===
proceed?

# Retrieve all services
services = call_esp(ESP::Service.method(:all), []) 

# Retrieve all external accounts
external_account_ids.each do |external_account_id|
    external_account = call_esp(ESP::ExternalAccount.method(:find), [external_account_id])
    
    # Retrieve current intervals
    scan_intervals = call_esp(external_account.method(:scan_intervals), [])
    service_id_to_scan_interval = Hash.new
    scan_intervals.each do |scan_interval|
        service_id_to_scan_interval[scan_interval.service_id] = scan_interval
    end

    services.each do |service|
        if service_id_to_scan_interval.key? service.id
            scan_interval = service_id_to_scan_interval[service.id]

            if (scan_interval.interval != INTERVAL)
                scan_interval.interval = INTERVAL
                call_esp(scan_interval.method(:save), [])
            end
        else
            scan_interval = call_esp(ESP::ScanInterval.method(:create), [interval: INTERVAL, external_account_id: external_account.id, service_id: service.id])
        end

        puts "Set Account #{external_account.name} - #{service.name} to #{INTERVAL} minutes."
    end
end
#=== End Main Script ===
