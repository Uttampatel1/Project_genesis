import os

def merge_python_files(output_file="merged_code.txt"):
    with open(output_file, "w", encoding="utf-8") as outfile:
        for filename in os.listdir():
            if filename.endswith(".py") and filename != os.path.basename(__file__):  # Avoid reading itself
                with open(filename, "r", encoding="utf-8") as infile:
                    outfile.write(f"# Contents of {filename}\n")
                    outfile.write(infile.read() + "\n\n")
    print(f"All Python files have been merged into {output_file}")

if __name__ == "__main__":
    merge_python_files()
