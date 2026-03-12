import sys
import os

# Add backend directory to sys.path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.parser import parse_docx_to_markdown

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_parser.py <path_to_docx_file>")
        sys.exit(1)
        
    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' not found.")
        sys.exit(1)
        
    print(f"Parsing '{filepath}'...")
    try:
        markdown_output = parse_docx_to_markdown(filepath)
        
        # Save output to a markdown file with the same name
        output_path = f"{os.path.splitext(filepath)[0]}_parsed.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_output)
            
        print(f"Success! Output saved to: {output_path}")
        print(markdown_output[:50000])
        print("---------------------------------------\n")
        
    except Exception as e:
        print(f"Error during parsing: {e}")

if __name__ == "__main__":
    main()
