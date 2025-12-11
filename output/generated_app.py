#!/usr/bin/env python3
"""Simple calculator program."""
import sys

def add(a, b):
    """Add two numbers."""
    return a + b

def subtract(a, b):
    """Subtract b from a."""
    return a - b

def multiply(a, b):
    """Multiply two numbers."""
    return a * b

def divide(a, b):
    """Divide a by b."""
    if b == 0:
        return "Error: Division by zero"
    return a / b

def main():
    """Main calculator function."""
    print("Simple Calculator")
    print("Operations: +, -, *, /")

    try:
        num1 = float(input("Enter first number: "))
        operator = input("Enter operator (+, -, *, /): ")
        num2 = float(input("Enter second number: "))

        if operator == '+':
            result = add(num1, num2)
        elif operator == '-':
            result = subtract(num1, num2)
        elif operator == '*':
            result = multiply(num1, num2)
        elif operator == '/':
            result = divide(num1, num2)
        else:
            result = "Error: Invalid operator"

        print(f"Result: {result}")
    except ValueError:
        print("Error: Please enter valid numbers")
    except KeyboardInterrupt:
        print("Calculator closed")

if __name__ == "__main__":
    main()
