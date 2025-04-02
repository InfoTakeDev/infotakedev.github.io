import os
import re
import yaml  # To read the config file

# Calculate path relative to the script file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CONFIG_FILE = os.path.join(PROJECT_ROOT, "etc", "config.yaml")
HTML_FILE = "index.html"
print(f'{SCRIPT_DIR} {PROJECT_ROOT} {CONFIG_FILE} {HTML_FILE}')

def load_config(config_path=CONFIG_FILE):
    """Loads service configuration from a YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        if not config or 'services' not in config:
            print(f"Error: Invalid config file format in {config_path}")
            return None
        # Basic validation for expected fields (name, port, fqdn), tag is optional
        valid_services = []
        for service in config['services']:
            if 'name' in service and 'port' in service and 'fqdn' in service:
                # Add the service, tag will be handled later if missing
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

        for service in services:
            service_name = service['name']
            port = service['port']
            fqdn = service['fqdn']
            tag = service.get('tag')  # Get tag, returns None if not present

            # Use tag for ID if present, otherwise use name
            if tag:
                service_id_base = tag.lower().replace(' ', '-')  # Sanitize tag like name
                print(
                    f"  Processing {service_name} (Tag: {tag}, Port {port}) -> {fqdn} using tag for ID base '{service_id_base}'")
            else:
                service_id_base = service_name.lower().replace(' ', '-')  # Sanitize name
                print(
                    f"  Processing {service_name} (Port {port}) -> {fqdn} using name for ID base '{service_id_base}'")

            # --- Update the link (<a> tag) ---
            # Regex to find the <a> tag by its ID, capture parts around href and the content
            # Regex updated to use the name-based service_id_base
            # Regex to find the <a> tag by its ID and the <span> by its ID, capturing necessary parts
            # This version is more robust to attribute order (id="..." href="..." vs href="..." id="...")
            print(f"    Attempting to find link ID: '{service_id_base}-link'")
            print(f"    Attempting to find span ID: '{service_id_base}-fqdn'")
            pattern_link = re.compile(
                # Capture the opening <a> tag up to the href attribute value
                rf'(<a\s+(?:[^>]*\s+)?href=")[^"]*'
                # Capture the rest of the <a> tag attributes, including the correct id
                rf'("(?:\s+[^>]*)?\s+id="{re.escape(service_id_base)}-link"(?:[^>]*)*>)'
                # Capture the text content before the span
                rf'([^<]*)'
                # Capture the opening <span> tag, including the correct id
                rf'(<span\s+[^>]*id="{re.escape(service_id_base)}-fqdn"[^>]*>)'
                # Match the existing content inside the span
                rf'[^<]*'
                # Capture the closing span and closing a tags
                rf'(</span>\s*</a>)',
                re.IGNORECASE | re.DOTALL
            )

            # Replacement string using captured groups and data from config
            # Use the actual fqdn value, not re.escape() for the replacement text
            # Replace \g<3> (original text before span) with the service_name
            replacement_link = rf'\g<1>{fqdn}\g<2>{service_name} \g<4>{fqdn}\g<5>'

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
