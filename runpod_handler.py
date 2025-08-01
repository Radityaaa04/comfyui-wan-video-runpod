import runpod
import subprocess
import requests
import json
import time
import os
import base64

# ComfyUI API endpoint
COMFYUI_URL = "http://127.0.0.1:8188"

def start_comfyui():
    """Start ComfyUI server"""
    print("Starting ComfyUI...")
    
    # Start ComfyUI in background
    process = subprocess.Popen([
        "python", "/workspace/ComfyUI/main.py",
        "--listen", "127.0.0.1", 
        "--port", "8188"
    ])
    
    # Wait for ComfyUI to start
    for i in range(30):
        try:
            response = requests.get(f"{COMFYUI_URL}/system_stats")
            if response.status_code == 200:
                print("ComfyUI started successfully!")
                return process
        except:
            time.sleep(2)
    
    print("Failed to start ComfyUI")
    return None

def queue_prompt(prompt):
    """Queue prompt to ComfyUI"""
    try:
        # Generate unique client_id
        client_id = str(int(time.time()))
        
        # Queue the prompt
        data = {
            "prompt": prompt,
            "client_id": client_id
        }
        
        response = requests.post(f"{COMFYUI_URL}/prompt", json=data)
        
        if response.status_code == 200:
            result = response.json()
            prompt_id = result["prompt_id"]
            return prompt_id, client_id
        else:
            return None, None
            
    except Exception as e:
        print(f"Error queuing prompt: {e}")
        return None, None

def get_result(prompt_id):
    """Get result from ComfyUI"""
    try:
        # Wait for completion
        for i in range(120):  # 2 minutes timeout
            response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
            
            if response.status_code == 200:
                history = response.json()
                
                if prompt_id in history:
                    # Get output images/videos
                    outputs = history[prompt_id]["outputs"]
                    results = []
                    
                    for node_id, output in outputs.items():
                        if "images" in output:
                            for image_info in output["images"]:
                                filename = image_info["filename"]
                                # Get image data
                                img_response = requests.get(f"{COMFYUI_URL}/view?filename={filename}")
                                if img_response.status_code == 200:
                                    img_base64 = base64.b64encode(img_response.content).decode()
                                    results.append({
                                        "type": "image",
                                        "filename": filename,
                                        "data": img_base64
                                    })
                        
                        if "videos" in output:
                            for video_info in output["videos"]:
                                filename = video_info["filename"]
                                # Get video data
                                vid_response = requests.get(f"{COMFYUI_URL}/view?filename={filename}")
                                if vid_response.status_code == 200:
                                    vid_base64 = base64.b64encode(vid_response.content).decode()
                                    results.append({
                                        "type": "video",
                                        "filename": filename,
                                        "data": vid_base64
                                    })
                    
                    return results
            
            time.sleep(1)
        
        return None
        
    except Exception as e:
        print(f"Error getting result: {e}")
        return None

# ComfyUI workflow for text-to-video
def create_wan_video_workflow(prompt, width=512, height=512, frames=16):
    """Create ComfyUI workflow for Wan Video"""
    workflow = {
        "1": {
            "inputs": {
                "text": prompt,
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "2": {
            "inputs": {
                "text": "",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "3": {
            "inputs": {
                "seed": int(time.time()),
                "steps": 20,
                "cfg": 7.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "positive": ["1", 0],
                "negative": ["2", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "4": {
            "inputs": {
                "ckpt_name": "wan-video-14b.safetensors"  # Model file
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "5": {
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": frames
            },
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode"
        },
        "7": {
            "inputs": {
                "images": ["6", 0],
                "filename_prefix": "wan_video_output",
                "format": "video/h264-mp4",
                "pingpong": False,
                "save_output": True
            },
            "class_type": "VHS_VideoCombine"
        }
    }
    
    return workflow

def handler(job):
    """Main handler"""
    try:
        # Start ComfyUI if not running
        if not hasattr(handler, 'comfyui_process'):
            handler.comfyui_process = start_comfyui()
            
        if not handler.comfyui_process:
            return {"error": "Failed to start ComfyUI"}
        
        # Get job input
        job_input = job.get("input", {})
        prompt = job_input.get("prompt", "A beautiful landscape")
        width = job_input.get("width", 512)
        height = job_input.get("height", 512)
        frames = job_input.get("frames", 16)
        
        # Create workflow
        workflow = create_wan_video_workflow(prompt, width, height, frames)
        
        # Queue prompt
        prompt_id, client_id = queue_prompt(workflow)
        
        if not prompt_id:
            return {"error": "Failed to queue prompt"}
        
        # Get result
        results = get_result(prompt_id)
        
        if results:
            return {
                "status": "success",
                "prompt": prompt,
                "results": results,
                "prompt_id": prompt_id
            }
        else:
            return {"error": "Failed to get results"}
            
    except Exception as e:
        return {"error": str(e)}

# Initialize ComfyUI process
handler.comfyui_process = None

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
