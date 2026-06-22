from typing import List, Dict, Any
from datetime import datetime
import os

from shared.branding import DEFAULT_DISPLAY_NAME


class CodePrinter:
    """Service for generating printable code sheets."""
    
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(__file__), "templates")
    
    def generate_html(
        self,
        codes: List[Dict[str, Any]],
        batch_info: Dict[str, Any],
    ) -> str:
        """Generate HTML for printing codes."""
        duration = batch_info.get("duration_minutes", 60)
        batch_id = batch_info.get("id", 0)
        value = batch_info.get("value_per_code", 0)
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Batch #{batch_id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Courier New', monospace;
            background: white;
            padding: 20px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 20px;
            border-bottom: 2px solid #000;
            padding-bottom: 10px;
        }}
        .header h1 {{
            font-size: 24px;
            margin-bottom: 5px;
        }}
        .header p {{
            font-size: 14px;
            color: #666;
        }}
        .codes-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
        }}
        .code-box {{
            border: 2px dashed #000;
            padding: 15px;
            width: 220px;
            text-align: center;
            background: #fafafa;
            page-break-inside: avoid;
        }}
        .code-value {{
            font-size: 24px;
            font-weight: bold;
            letter-spacing: 2px;
            margin: 10px 0;
            color: #000;
        }}
        .code-info {{
            font-size: 12px;
            color: #666;
            border-top: 1px solid #ccc;
            padding-top: 8px;
            margin-top: 8px;
        }}
        .footer {{
            margin-top: 20px;
            text-align: center;
            font-size: 10px;
            color: #999;
            border-top: 1px solid #ccc;
            padding-top: 10px;
        }}
        @media print {{
            body {{
                padding: 0;
            }}
            .code-box {{
                border: 2px dashed #000;
                background: white;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{DEFAULT_DISPLAY_NAME}</h1>
        <p>Access Code Batch #{batch_id}</p>
        <p>Duration: {duration} minutes | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    
    <div class="codes-container">
"""
        
        for code in codes:
            code_value = code.get("code", "")
            html += f"""
        <div class="code-box">
            <div class="code-value">{code_value}</div>
            <div class="code-info">
                Duration: {duration} minutes<br>
                Value: ₦{value}
            </div>
        </div>
"""
        
        html += """
    </div>
    
    <div class="footer">
        <p>Present this code at the counter to start your session</p>
        <p>Codes are single-use and expire after use</p>
    </div>
</body>
</html>
"""
        
        return html
    
    def generate_text(
        self,
        codes: List[Dict[str, Any]],
        batch_info: Dict[str, Any],
    ) -> str:
        """Generate plain text for printing codes."""
        duration = batch_info.get("duration_minutes", 60)
        batch_id = batch_info.get("id", 0)
        value = batch_info.get("value_per_code", 0)
        
        text = f"""
===============================================
           {DEFAULT_DISPLAY_NAME.upper()} ACCESS CODES
===============================================
Batch ID: #{batch_id}
Duration: {duration} minutes
Value: ₦{value} per code
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
===============================================

"""
        
        for i, code in enumerate(codes, 1):
            code_value = code.get("code", "")
            text += f"{i:3d}. {code_value}\n"
        
        text += """
===============================================
        PRESENT CODE AT COUNTER
===============================================
"""
        
        return text
    
    def save_html(
        self,
        codes: List[Dict[str, Any]],
        batch_info: Dict[str, Any],
        output_path: str,
    ) -> str:
        """Save HTML to file for printing."""
        html = self.generate_html(codes, batch_info)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        
        return output_path
    
    def save_text(
        self,
        codes: List[Dict[str, Any]],
        batch_info: Dict[str, Any],
        output_path: str,
    ) -> str:
        """Save text to file for printing."""
        text = self.generate_text(codes, batch_info)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        return output_path


code_printer = CodePrinter()
