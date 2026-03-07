import argparse
import webbrowser
from fintelpy import Fintelpy

def generate_report(profile_url: str):
    """
    Generates an OSINT report for a given Facebook profile URL.
    """
    try:
        # Initialize Fintelpy with the profile URL
        fintel = Fintelpy(profile_url)
        print(f"[*] Starting OSINT scan for: {profile_url}")

        # --- Account Information ---
        print("\n" + "="*20)
        print("Account Information")
        print("="*20)
        account_info_url = fintel.account()
        print(f"[*] Account Info URL: {account_info_url}")
        # In a real scenario, you would open this URL and parse it.
        # For this script, we will just display the generated link.

        # --- Searching for Public Posts ---
        print("\n" + "="*20)
        print("Public Posts Search")
        print("="*20)
        posts_url = fintel.search_posts()
        print(f"[*] Public Posts URL: {posts_url}")
        print("  > This URL searches for all public posts made by the user.")

        # --- Searching for Tagged Photos ---
        print("\n" + "="*20)
        print("Tagged Photos Search")
        print("="*20)
        photos_url = fintel.search_photos()
        print(f"[*] Tagged Photos URL: {photos_url}")
        print("  > This URL searches for photos the user is tagged in.")

        # --- Searching for Public Videos ---
        print("\n" + "="*20)
        print("Public Videos Search")
        print("="*20)
        videos_url = fintel.search_videos()
        print(f"[*] Public Videos URL: {videos_url}")
        print("  > This URL searches for public videos posted by the user.")

        # --- People Search (Example: People with same name) ---
        # This requires extracting the name first, which is complex.
        # The tool is better used for known employers, schools, etc.
        # For simplicity, we will skip this in the automated script.

        print("\n[*] Scan Finished. The URLs above provide direct access to filtered search results.")
        print("[*] Manual analysis of these pages is required to gather intelligence.")

    except Exception as e:
        print(f"[!] An error occurred: {e}")
        print("[!] This might be due to an invalid URL, a private profile, or changes in Facebook's structure.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Facebook OSINT Report Generator")
    parser.add_argument("profile_url", help="The full URL of the Facebook profile to scan.")
    args = parser.parse_args()
    
    generate_report(args.profile_url)
