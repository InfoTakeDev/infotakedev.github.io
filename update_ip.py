import os
import re
import yaml  # To read the config file

CONFIG_FILE = "config.yaml"
HTML_FILE = "index.html"


def load_config(config_path=CONFIG_FILE):
    """Loads service configuration from a YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        if not config or 'services' not in config:
            print(f"Error: Invalid config file format in {config_path}")
            return None
        # Basic validation for expected fields (name, port, fqdn)
        valid_services = []
        for service in config['services']:
            if 'name' in service and 'port' in service and 'fqdn' in service:
                valid_services.append(service)
            else:
                print(
                    f"Warning: Service entry missing required fields (name, port, fqdn): {service}. Skipping.")
        return valid_services
    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}")
        return None
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {config_path}: {e}")
        return None
    except Exception as e:
        print(f"Error loading config: {e}")
        return None


def update_html_from_config(html_path, services):
    """Reads an HTML file, updates FQDN placeholders and links based on service config, and writes it back."""
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        original_html = html_content  # Keep a copy for comparison
        updates_made = False

        print(f"Updating {html_path} based on {CONFIG_FILE}...")

        for service in services:  # Removed enumerate, index 'i' no longer needed
            service_name = service['name']
            port = service['port']
            fqdn = service['fqdn']
            # Construct IDs dynamically based on sanitized service name (e.g., "Service 1" -> "service-1")
            service_id_base = service_name.lower().replace(' ', '-')

            print(
                f"  Processing {service_name} (Port {port}) -> {fqdn} for ID base '{service_id_base}'")

            # --- Update the link (<a> tag) ---
            # Regex to find the <a> tag by its ID, capture parts around href and the content
            # Regex updated to use the name-based service_id_base
            pattern_link = re.compile(
                # Capture start of tag and href using name-based ID
                rf'(<a\s+[^>]*id="{re.escape(service_id_base)}-link"[^>]*\s+href=")[^"]*("[^>]*>)'
                # Capture existing text content (like "Service 1 (Port 9000): ")
                rf'([^<]+)'
                # Capture start of span using name-based ID
                rf'(<span\s+[^>]*id="{re.escape(service_id_base)}-fqdn"[^>]*>)'
                # Match existing span content (placeholder or old URL)
                rf'[^<]+'
                rf'(</span>\s*</a>)',  # Capture end of span and end of link
                re.IGNORECASE | re.DOTALL
            )

            # Replacement string using captured groups and data from config
            # Ensure FQDN is properly escaped if it contains special regex characters (unlikely for URLs)
            replacement_link = rf'\g<1>{re.escape(fqdn)}\g<2>{service_name} (Port {port}): \g<4>{re.escape(fqdn)}\g<5>'

            # Perform the substitution
            new_html_content = pattern_link.sub(replacement_link, html_content)

            print(new_html_content)
            if new_html_content != html_content:
                updates_made = True
                html_content = new_html_content  # Update content for the next iteration
                print(f"    Updated elements for {service_id_base}")
            else:
                print(
                    f"    Warning: Could not find or update elements for {service_id_base}. Check HTML structure and IDs.")

        # Write only if changes were made
        if updates_made:
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"Successfully updated {html_path}")
        else:
            print(f"No changes needed in {html_path}.")

        return updates_made

    except FileNotFoundError:
        print(f"Error: HTML file not found at {html_path}")
    except Exception as e:
        print(f"An error occurred during HTML update: {e}")


if __name__ == "__main__":
    print("Attempting to update HTML based on config file...")
    services_config = load_config(CONFIG_FILE)

    if services_config:
        update_html_from_config(HTML_FILE, services_config)
    else:
        print(
            f"Could not load valid service configurations from {CONFIG_FILE}. HTML not updated.")
