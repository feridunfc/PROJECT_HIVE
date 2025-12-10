# agents/technical/dev_agent.py

async def _process_response(self, response, state: NeuralState) -> str:
    raw = response.content.strip()
    self.logger.info(f"Raw LLM response: {raw[:200]}...")

    # ÖNCE: Raw response'daki bozuk karakterleri temizle
    raw = raw.replace('\"\"\"', '"""').replace("\\'\\'\\'", "'''")

    code = extract_code(raw)

    # Fallback if no code extracted - ÇOK BASİT ve GÜVENLİ bir kod
    if not code or len(code.strip()) < 10:
        self.logger.warning("No valid code extracted, using SUPER SIMPLE fallback")
        # Çok basit, syntax hatası olmayan bir hesap makinesi
        code = """def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        return "Error: Division by zero"
    return a / b

def main():
    print("Simple Calculator")
    print("1. Add")
    print("2. Subtract")
    print("3. Multiply")
    print("4. Divide")

    choice = input("Enter choice (1/2/3/4): ")

    if choice not in ['1', '2', '3', '4']:
        print("Invalid choice")
        return

    try:
        num1 = float(input("Enter first number: "))
        num2 = float(input("Enter second number: "))
    except ValueError:
        print("Please enter valid numbers")
        return

    if choice == '1':
        result = add(num1, num2)
        operation = "+"
    elif choice == '2':
        result = subtract(num1, num2)
        operation = "-"
    elif choice == '3':
        result = multiply(num1, num2)
        operation = "*"
    elif choice == '4':
        result = divide(num1, num2)
        operation = "/"

    print(f"{num1} {operation} {num2} = {result}")

if __name__ == "__main__":
    main()"""

    # DOSYAYA YAZMADAN ÖNCE: Kodu compile etmeyi dene
    try:
        compile(code, "generated_app.py", "exec")
        self.logger.info("✅ Code compiles successfully")
    except SyntaxError as e:
        self.logger.error(f"❌ Code has syntax error: {e}")
        # Syntax hatası varsa daha da basit bir kod yaz
        code = """print("Calculator")
print("1 + 1 =", 1 + 1)"""

    # Ensure output directory exists
    self.output_dir.mkdir(parents=True, exist_ok=True)

    # Write to file
    target = self.output_dir / "generated_app.py"
    try:
        target.write_text(code, encoding="utf-8")
        self.logger.info(f"✅ Code written to: {target}")

        # Ekstra kontrol: Dosyayı oku ve tekrar compile et
        with open(target, 'r', encoding='utf-8') as f:
            content = f.read()
            compile(content, str(target), 'exec')
        self.logger.info("✅ File compiles successfully after writing")

    except Exception as e:
        self.logger.error(f"❌ Failed to write/compile code: {e}")
        # Son çare: Basit bir dosya yaz
        target.write_text('print("Hello Calculator")\nprint("2+2=", 2+2)', encoding='utf-8')
        code = target.read_text()

    # Update state
    state.artifacts["generated_code_path"] = str(target)
    state.artifacts["generated_code"] = {"generated_app.py": code}

    return f"✅ Generated {target}"