import os
import argparse
from pathlib import Path
from markdownify import markdownify as md
from bs4 import BeautifulSoup

def convert_html_to_markdown(source_dir="_build/html", output_dir="_build/markdown"):
    """
    Convert Sphinx-generated HTML files under source_dir to markdown files in output_dir.
    Only converts the main document content, excluding navigation and sidebars.
    
    Args:
        source_dir (str): Directory containing HTML files to convert
        output_dir (str): Directory where markdown files will be saved
    """
    source_path = Path(source_dir)
    output_path = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Walk through all files in the source directory
    for root, dirs, files in os.walk(source_path):
        for file in files:
            if file.endswith('.html'):
                # Get the full path of the HTML file
                html_file_path = Path(root) / file
                
                # Calculate relative path to maintain directory structure
                relative_path = html_file_path.relative_to(source_path)
                
                # Create corresponding markdown file path
                md_file_path = output_path / relative_path.with_suffix('.md')
                
                # Create subdirectories if needed
                md_file_path.parent.mkdir(parents=True, exist_ok=True)
                
                try:
                    # Read HTML file
                    with open(html_file_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    # Parse HTML and extract main document content
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Find the main document div (Sphinx-specific)
                    main_content = soup.find('div', {'class': 'document', 'role': 'main'})
                    
                    if main_content:
                        # Convert only the main content to markdown
                        markdown_content = md(str(main_content))
                        
                        # Write markdown file
                        with open(md_file_path, 'w', encoding='utf-8') as f:
                            f.write(markdown_content)
                        
                        print(f"Converted: {html_file_path} -> {md_file_path}")
                    else:
                        print(f"Warning: No main document content found in {html_file_path}")
                        # Fallback to converting entire HTML if main content not found
                        markdown_content = md(html_content)
                        with open(md_file_path, 'w', encoding='utf-8') as f:
                            f.write(markdown_content)
                        print(f"Converted (fallback): {html_file_path} -> {md_file_path}")
                    
                except Exception as e:
                    print(f"Error converting {html_file_path}: {str(e)}")
    
    print(f"Conversion complete! Markdown files saved in: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert Sphinx-generated HTML files to Markdown format."
    )
    parser.add_argument(
        "--source", 
        "-s", 
        default="_build/html",
        help="Directory containing HTML files to convert (default: _build/html)"
    )
    parser.add_argument(
        "--output", 
        "-o", 
        default="_build/markdown",
        help="Directory where markdown files will be saved (default: _build/markdown)"
    )
    
    args = parser.parse_args()
    
    print(f"Converting HTML files from: {args.source}")
    print(f"Output directory: {args.output}")
    print("-" * 50)
    
    convert_html_to_markdown(args.source, args.output)

