#!/usr/bin/env python3
"""Build a short inspirational message and print it."""


def build_message():
    parts = ["Good", "Girls", "Build", "Better", "Worlds"]
    message = " ".join(parts)
    return message.capitalize()


def main():
    print(build_message())


if __name__ == "__main__":
    main()
