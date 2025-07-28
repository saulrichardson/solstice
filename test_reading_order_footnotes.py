"""Test the reading order algorithm with footnotes."""

from src.injestion.models.box import Box
from src.injestion.processing.reading_order import determine_reading_order_simple


def test_footnote_ordering():
    """Test that full-width bottom elements (footnotes) are read last."""
    
    # Create test boxes simulating a two-column layout with footnotes
    boxes = [
        # Left column content
        Box(id="title", bbox=[100, 100, 700, 150], page_index=0, label="Title"),
        Box(id="left1", bbox=[100, 200, 700, 800], page_index=0, label="Text"),
        Box(id="left2", bbox=[100, 850, 700, 1400], page_index=0, label="Text"),
        
        # Right column content  
        Box(id="right1", bbox=[850, 200, 1450, 800], page_index=0, label="Text"),
        Box(id="right2", bbox=[850, 850, 1450, 1400], page_index=0, label="Text"),
        
        # Full-width footnote at bottom
        Box(id="footnote1", bbox=[100, 2400, 1450, 2500], page_index=0, label="Text"),
        Box(id="footnote2", bbox=[100, 2550, 1450, 2650], page_index=0, label="Text"),
        
        # Page number (also full-width at bottom)
        Box(id="pagenum", bbox=[600, 2800, 1000, 2850], page_index=0, label="Text"),
    ]
    
    # Run the algorithm
    reading_order = determine_reading_order_simple(boxes, page_width=1600)
    
    print("Reading order:")
    for i, box_id in enumerate(reading_order, 1):
        box = next(b for b in boxes if b.id == box_id)
        width = box.bbox[2] - box.bbox[0]
        width_pct = (width / 1600) * 100
        print(f"{i}. {box_id:10} (width: {width_pct:.0f}%, y: {box.bbox[1]})")
    
    # Verify footnotes come last
    footnote_indices = [reading_order.index(id) for id in ["footnote1", "footnote2", "pagenum"]]
    regular_indices = [reading_order.index(id) for id in ["title", "left1", "left2", "right1", "right2"]]
    
    assert all(fn_idx > max(regular_indices) for fn_idx in footnote_indices), \
        "Footnotes should come after all regular content"
    
    print("\n✓ Test passed: Footnotes are correctly placed at the end!")


if __name__ == "__main__":
    test_footnote_ordering()