# Vision Agent Interface Design

## Use Case: BCC Agent with Vision LLM

The BCC agent needs to pass actual images to vision-capable LLMs (GPT-4V, Claude 3, etc.)

## Current Problem
```python
# Current approach - only gets placeholders
interface = FactCheckInterface(document)
text = interface.get_full_text()
# "Results shown in [FIGURE 1 - See figure_p3_123.png]"
# LLM can't see the actual figure!
```

## Solution: Enhanced Reader for Vision Agents

```python
# src/interfaces/readers.py

from PIL import Image
import base64
from io import BytesIO

class VisionContent:
    """Content item that can include images."""
    def __init__(self, content_type: str, text: str = None, image_path: str = None):
        self.type = content_type
        self.text = text
        self.image_path = image_path
        self._image_cache = None
    
    def get_image(self) -> Image.Image:
        """Load image lazily."""
        if self.image_path and not self._image_cache:
            self._image_cache = Image.open(self.image_path)
        return self._image_cache
    
    def get_image_base64(self) -> str:
        """Get image as base64 for API calls."""
        img = self.get_image()
        if img:
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode()
        return None

class DocumentReader(ABC):
    # ... other methods ...
    
    @abstractmethod
    def get_vision_content(self, include_images: bool = True) -> List[VisionContent]:
        """Get content formatted for vision LLMs."""
        pass

class StandardDocumentReader(DocumentReader):
    
    def get_vision_content(self, include_images: bool = True) -> List[VisionContent]:
        """Get content with actual images for vision LLMs."""
        content_items = []
        
        for page_idx, block_ids in enumerate(self.document.reading_order):
            for block_id in block_ids:
                block = self._get_block_by_id(block_id)
                
                if block.text:
                    # Text content
                    content_items.append(
                        VisionContent(content_type="text", text=block.text)
                    )
                elif block.image_path and include_images:
                    # Actual image content
                    content_items.append(
                        VisionContent(
                            content_type=block.role.lower(),  # 'figure' or 'table'
                            image_path=block.image_path,
                            text=f"{block.role} from page {page_idx + 1}"
                        )
                    )
        
        return content_items
```

## BCC Agent Implementation

```python
# src/fact_check/agents/bcc_vision_agent.py

from src.interfaces.document import Document
from src.interfaces.readers import StandardDocumentReader
from anthropic import Anthropic

class BCCVisionAgent:
    """Agent that uses vision LLM to analyze documents."""
    
    def __init__(self):
        self.client = Anthropic()
    
    def analyze_with_vision(self, document: Document, query: str) -> str:
        """Analyze document including images."""
        reader = StandardDocumentReader(document)
        content_items = reader.get_vision_content()
        
        # Build messages for vision LLM
        messages = []
        current_content = []
        
        for item in content_items:
            if item.type == "text":
                current_content.append({
                    "type": "text",
                    "text": item.text
                })
            elif item.type in ["figure", "table"]:
                # Add actual image
                current_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": item.get_image_base64()
                    }
                })
                # Add caption
                if item.text:
                    current_content.append({
                        "type": "text", 
                        "text": item.text
                    })
        
        messages.append({
            "role": "user",
            "content": current_content + [{
                "type": "text",
                "text": f"\n\nQuestion: {query}"
            }]
        })
        
        # Call vision LLM
        response = self.client.messages.create(
            model="claude-3-opus-20240229",
            messages=messages,
            max_tokens=1000
        )
        
        return response.content[0].text
```

## Usage Examples

### 1. BCC Agent Analyzing Charts
```python
agent = BCCVisionAgent()
result = agent.analyze_with_vision(
    document,
    "What trends are shown in the efficacy charts?"
)
# LLM can now SEE the actual charts and provide detailed analysis
```

### 2. Fact Checking with Visual Evidence
```python
# Check claims about visual data
content = reader.get_vision_content()

for item in content:
    if item.type == "figure":
        # Send to vision LLM for analysis
        analysis = analyze_figure(item.get_image(), claim_text)
```

### 3. Mixed Mode Analysis
```python
# Some agents might want text-only, others need images
if agent.has_vision_capability:
    content = reader.get_vision_content(include_images=True)
else:
    content = reader.get_text_only()
```

## Benefits for BCC/Vision Agents

1. **Direct Image Access**: No more "see figure X" - LLM actually sees it
2. **Lazy Loading**: Images loaded only when needed
3. **Format Flexibility**: Base64 for APIs, PIL for processing
4. **Maintains Order**: Images appear in correct document flow
5. **Graceful Degradation**: Can fall back to text-only if needed

## Other Vision Use Cases

- **Table Extraction**: Vision LLM can read complex tables
- **Chart Analysis**: Extract data points from graphs
- **Diagram Understanding**: Comprehend flowcharts, diagrams
- **Screenshot Analysis**: For UI documentation
- **Medical Images**: Analyze scans, x-rays (with appropriate models)

This interface design ensures that vision-capable agents get the full document content they need!