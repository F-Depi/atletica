#!/bin/bash

# Navigate to the CSS folder
cd app/static/css || { echo "Directory app/static/css not found!"; exit 1; }

# List of files in order — you control the order here
files=(
    "variables.css"
    "base.css"
    "header.css"
    "components.css"
    "tables.css"
    "filters.css"
    "theme-toggle.css"
    "utilities.css"
    "footer.css"
    "responsive.css"
    "athlete.css"
)

# Output file
output="main.css"

# Clear old main.css if it exists
> "$output"

# Concatenate all files into main.css
for file in "${files[@]}"
do
    if [[ -f "$file" ]]; then
        echo "/* ===== $file ===== */" >> "$output"
        cat "$file" >> "$output"
        echo -e "\n" >> "$output"
    else
        echo "Warning: $file not found, skipping."
    fi
done

echo "CSS files have been combined into $output."

