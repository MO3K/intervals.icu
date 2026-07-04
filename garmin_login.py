#!/usr/bin/env python3
"""One-time Garmin Connect login → saves OAuth tokens to ~/.garminconnect.

Run interactively in YOUR terminal so credentials stay local:
    python3 garmin_login.py

Prompts for email, password (hidden), and MFA code if enabled.
After this, pull_weekly_data.py will merge RHR/HRV/sleep/weight automatically.
"""
import getpass
from garminconnect import Garmin
from coach.config import GARMIN_TOKEN_DIR


def main():
    email = input("Garmin email: ").strip()
    password = getpass.getpass("Garmin password: ")

    garmin = Garmin(email=email, password=password,
                    prompt_mfa=lambda: input("MFA code: ").strip())
    garmin.login()
    garmin.garth.dump(GARMIN_TOKEN_DIR)
    print(f"\n✅ Tokens saved to {GARMIN_TOKEN_DIR}")
    print("Now run: python3 pull_weekly_data.py --refresh-wellness")


if __name__ == "__main__":
    main()
