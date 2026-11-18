#!/usr/bin/env python3
"""A tiny script that greets someone by name."""


def greet(name):
    """Return a friendly greeting for the given name."""
    return f"Hello, {name}! Gemi here — nice to meet you."


def main():
    """Print a greeting when the script is run directly."""
    print(greet("you"))


if __name__ == "__main__":
    main()
