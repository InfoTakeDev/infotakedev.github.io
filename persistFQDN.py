import ngrok
import time
import os
import yaml  # For reading/writing config file
# Retrieve ngrok authtoken from environment variable or use a default
# Replace with your token if not using env var
NGROK_AUTHTOKEN = os.environ.get(
    "NGROK_AUTHTOKEN", "YOUR_DEFAULT_NGROK_AUTHTOKEN_HERE")

# NGROK_AUTHTOKEN = "2W9sEja5fHRYq3B9uwXHSgOg2lU_4uHUPbaNBLGtufR2d1J1u" # Keep if hardcoding needed, otherwise use env var

CONFIG_FILE = "config.yaml"


def load_config(config_path=CONFIG_FILE):
    """Loads service configuration from a YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        if not config or 'services' not in config:
            print(f"Error: Invalid config file format in {config_path}")
            return None
        # Ensure ports are integers
        for service in config['services']:
            if 'port' in service:
                try:
                    service['port'] = int(service['port'])
                except (ValueError, TypeError):
                    print(
                        f"Warning: Invalid port '{service['port']}' for service '{service.get('name', 'Unnamed')}'. Skipping.")
                    # Optionally remove the service or handle differently
                    # For now, let it potentially fail later if port is needed as int
            else:
                print(
                    f"Warning: Service '{service.get('name', 'Unnamed')}' missing 'port'. Skipping.")
                # Mark service as invalid or remove?

        return config['services']
    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}")
        return None
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {config_path}: {e}")
        return None
    except Exception as e:
        print(f"Error loading config: {e}")
        return None


def start_ngrok_tunnel(port, authtoken):
    """Starts an ngrok tunnel for the specified port."""
    try:
        ip = "localhost"
        port = port

        # Create a tunnel forwarding traffic to the specified IP and port
        listener = ngrok.connect(
            f"{ip}:{port}", proto="http", authtoken=authtoken)
        # Print statement moved to main loop for better context
        return listener
    except Exception as e:
        print(f"Error starting ngrok tunnel for port {port}: {e}")
        return None


def save_config(config_path, services_data):
    """Saves the service configuration data (including FQDNs) back to the YAML file."""
    try:
        # Structure the data back into the expected format { 'services': [...] }
        output_data = {'services': services_data}
        with open(config_path, 'w') as f:
            # Use sort_keys=False to maintain order from original file as much as possible
            yaml.dump(output_data, f, default_flow_style=False, sort_keys=False)
        print(f"Successfully updated {config_path} with FQDNs.")
        return True
    except Exception as e:
        print(f"Error saving config to {config_path}: {e}")
        return False


# --- Main Execution ---
if __name__ == "__main__":
    # Retrieve ngrok authtoken from environment variable or use a default
    NGROK_AUTHTOKEN = os.environ.get("NGROK_AUTHTOKEN")
    if not NGROK_AUTHTOKEN:
        # Fallback or specific token if needed for testing
        NGROK_AUTHTOKEN = "2W9sEja5fHRYq3B9uwXHSgOg2lU_4uHUPbaNBLGtufR2d1J1u"
        print(
            "Warning: NGROK_AUTHTOKEN environment variable not set. Using hardcoded token.")
        # Or exit:
        # print("Error: NGROK_AUTHTOKEN environment variable not set. Exiting.")
        # exit(1)

    services = load_config(CONFIG_FILE)
    listeners = {}
    # services list will be updated in place

    if services:
        try:
            print("Starting ngrok tunnels based on config.yaml...")
            all_started = True
            for service in services:
                # service is a dictionary reference from the services list
                name = service.get('name')
                port = service.get('port')

                # Basic validation
                if not name or not isinstance(port, int):
                    print(
                        f"Skipping invalid service entry: {service} (Name missing or port not an integer)")
                    continue

                print(f"  Attempting tunnel for: {name} (Port {port})")
                listener = start_ngrok_tunnel(port, NGROK_AUTHTOKEN)

                if listener:
                    print(
                        f"    Success: {listener.url()} -> http://localhost:{port}")
                    listeners[name] = listener
                    # Add/Update the 'fqdn' field in the service dictionary directly
                    service['fqdn'] = listener.url()
                else:
                    print(
                        f"    Failed to start tunnel for {name} (Port {port})")
                    all_started = False
                    # Decide if we should continue or exit if one fails
                    # For now, continue trying others

            # After attempting all tunnels
            if listeners:  # Check if at least one tunnel started
                print("\nActive ngrok tunnels:")
                for name, listener in listeners.items():
                    print(f"  {name}: {listener.url()}")

                # Save the updated service info (with FQDNs) back to config.yaml
                print(f"\nUpdating {CONFIG_FILE} with FQDNs...")
                # Pass the modified services list
                save_config(CONFIG_FILE, services)

                if not all_started:
                    print("\nWarning: One or more tunnels failed to start.")

                print("\nScript running. Press Ctrl+C to stop the tunnels.")
                # Keep the script running
                while True:
                    time.sleep(60)  # Check tunnels or just wait
            else:
                print("\nNo ngrok tunnels could be started successfully. Exiting.")

        except KeyboardInterrupt:
            print("\nCtrl+C detected. Closing ngrok listeners...")
            ngrok.disconnect()
            print("Tunnels closed.")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
            ngrok.disconnect()  # Ensure cleanup on unexpected errors
    else:
        print(f"Could not load services from {CONFIG_FILE}. Exiting.")
