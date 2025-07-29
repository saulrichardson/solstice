# Image Handling Strategy: Paths vs Data

## The Key Question
Should the Document model contain:
1. Image paths (current approach)
2. Actual image data
3. Both with lazy loading

## Current Approach: Paths Only

```python
class Block(BaseModel):
    image_path: str | None = None  # "figures/figure_p1_123.png"
```

## Option 1: Keep Paths, Load on Demand (RECOMMENDED)

```python
class Block(BaseModel):
    image_path: str | None = None  # Relative to document cache dir
    
class DocumentReader:
    def __init__(self, document: Document, base_path: Path = None):
        self.document = document
        self.base_path = base_path or Path(document.source).parent
    
    def load_image(self, block: Block) -> Image.Image:
        """Load image from path when needed."""
        if block.image_path:
            full_path = self.base_path / block.image_path
            return Image.open(full_path)
        return None
```

**Pros:**
- ✅ Small Document objects (good for serialization)
- ✅ Images loaded only when needed
- ✅ Easy to cache/store documents
- ✅ Can handle large documents with many images
- ✅ Paths are portable within the cache structure

**Cons:**
- ❌ Need to track base path
- ❌ Files must exist on disk
- ❌ More complex for remote storage

## Option 2: Embed Image Data

```python
class Block(BaseModel):
    image_path: str | None = None
    image_data: str | None = None  # Base64 encoded
    
    def get_image(self) -> Image.Image:
        if self.image_data:
            return Image.open(BytesIO(base64.b64decode(self.image_data)))
        return None
```

**Pros:**
- ✅ Self-contained documents
- ✅ No file system dependencies
- ✅ Easy to transmit over network

**Cons:**
- ❌ Large document files (base64 adds ~33% overhead)
- ❌ Memory intensive
- ❌ Slow to load/save documents
- ❌ Not suitable for large documents

## Option 3: Hybrid with References (IDEAL FOR SCALE)

```python
class ImageReference(BaseModel):
    """Reference to an image with multiple access methods."""
    local_path: str | None = None      # "figures/figure_p1_123.png"
    cache_key: str | None = None       # For distributed cache
    url: str | None = None             # For cloud storage
    checksum: str | None = None        # For verification
    
class Block(BaseModel):
    image_ref: ImageReference | None = None
    
class ImageResolver:
    """Resolves image references to actual data."""
    
    def __init__(self, cache_dir: Path = None, s3_client=None):
        self.cache_dir = cache_dir
        self.s3_client = s3_client
    
    def resolve(self, ref: ImageReference) -> Image.Image:
        # Try local path first
        if ref.local_path and self.cache_dir:
            path = self.cache_dir / ref.local_path
            if path.exists():
                return Image.open(path)
        
        # Try URL/S3
        if ref.url and self.s3_client:
            data = self.s3_client.get_object(ref.url)
            return Image.open(BytesIO(data))
        
        # Try distributed cache
        if ref.cache_key:
            data = distributed_cache.get(ref.cache_key)
            if data:
                return Image.open(BytesIO(data))
        
        raise FileNotFoundError(f"Could not resolve image: {ref}")
```

## Recommendation: Paths with Smart Loading

For the current system, I recommend **Option 1** (paths only) because:

1. **Ingestion produces files on disk** - Images are already saved
2. **Documents stay lightweight** - Can process large PDFs
3. **Easy to implement** - Minimal changes needed
4. **Future-proof** - Can add cloud storage later

## Implementation for Vision Agents

```python
class StandardDocumentReader:
    def __init__(self, document: Document):
        self.document = document
        # Infer base path from document source
        self.base_path = Path(document.source).parent.parent / "extracted"
    
    def get_vision_content(self) -> List[VisionContent]:
        """Load images on-demand for vision processing."""
        content = []
        
        for block in self._get_blocks_in_order():
            if block.text:
                content.append(VisionContent(type="text", text=block.text))
            elif block.image_path:
                # Load image when needed
                full_path = self.base_path / block.image_path
                content.append(VisionContent(
                    type=block.role.lower(),
                    image_path=full_path,  # Full path for loading
                    text=f"{block.role} from page {block.page_index + 1}"
                ))
        
        return content

# Usage in BCC agent
reader = StandardDocumentReader(document)
for item in reader.get_vision_content():
    if item.type in ["figure", "table"]:
        # Load image only when sending to LLM
        image_base64 = item.get_image_base64()  # Loads from disk
        messages.append({
            "type": "image",
            "source": {"type": "base64", "data": image_base64}
        })
```

## Future Migration Path

Start with paths → Add cloud storage → Add caching layer:

```python
# Phase 1: Local paths (now)
image_ref = ImageReference(local_path="figures/fig1.png")

# Phase 2: Add S3 (later)
image_ref = ImageReference(
    local_path="figures/fig1.png",
    url="s3://bucket/doc123/figures/fig1.png"
)

# Phase 3: Add caching (later)
image_ref = ImageReference(
    local_path="figures/fig1.png",
    url="s3://bucket/doc123/figures/fig1.png",
    cache_key="doc123:fig1:v1"
)
```

This approach gives us flexibility without over-engineering!