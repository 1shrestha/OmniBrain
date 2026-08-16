from typing import Dict, Any

class VisionAgent:
    def __init__(self, is_mock: bool = True):
        self.is_mock = is_mock

    def run(self, image_path: str) -> Dict[str, Any]:
        # Return a simple structured mock analysis for the demo
        if self.is_mock:
            return {
                "answer": f"Mock vision analysis for {image_path}: Detected a bar chart showing rising revenue."
            }
        return {"answer": "Vision Agent (real) not implemented in demo"}
