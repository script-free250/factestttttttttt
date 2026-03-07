import subprocess
import argparse
import json
import os

def analyze_profile(profile_url: str):
    """
    Analyzes a social media profile using social-analyzer.
    This script focuses on extracting information for a single username.
    """
    # The URL needs to be just the username for this tool.
    # e.g., "zuck" from "https://www.facebook.com/zuck"
    try:
        username = profile_url.split('/')[-1]
        if not username:
            # Handle URLs that end with a "/"
            username = profile_url.rstrip('/').split('/')[-1]
        
        print(f"[*] Extracted username: {username}")
        print(f"[*] Starting analysis for '{username}' on Facebook...")

        # Command to run social-analyzer for a specific user on a specific site
        command = [
            "social-analyzer",
            "--username", username,
            "--sites", "facebook",
            "--output", "json"
        ]

        # Run the command
        process = subprocess.run(command, capture_output=True, text=True)

        if process.returncode != 0:
            print("[!] An error occurred while running social-analyzer.")
            print(f"[!] Stderr: {process.stderr}")
            return

        print("[*] Analysis complete.")

        # The output is a string of JSON objects, one per line. We need to parse it.
        results = []
        for line in process.stdout.strip().split('\n'):
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"[!] Could not parse line: {line}")
                continue

        if not results:
            print("[!] No results found. The profile might be private or the username is incorrect.")
            return
        
        # Find the successful detection for Facebook
        facebook_result = None
        for res in results:
            if res.get("sitename") == "facebook" and res.get("status") == "FOUND":
                facebook_result = res
                break

        if facebook_result:
            print("\n" + "="*20)
            print("Report for:", facebook_result.get("username", "N/A"))
            print("="*20)
            print(f"  > Profile URL: {facebook_result.get('url', 'N/A')}")
            print(f"  > Detection Status: {facebook_result.get('status', 'N/A')}")
            # social-analyzer provides metadata if found, but often it just confirms existence.
            # The real value is the confirmed URL.
            print("\n[*] The tool has confirmed the existence of the profile at the URL above.")
            print("[*] Further manual OSINT is required by visiting the page.")
        else:
            print("[!] Could not find a valid, public Facebook profile for that username.")


    except Exception as e:
        print(f"[!] A critical error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Facebook OSINT Report Generator")
    parser.add_argument("profile_url", help="The full URL of the Facebook profile to scan.")
    args = parser.parse_args()
    
    analyze_profile(args.profile_url)
