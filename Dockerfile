FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Clone ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /workspace/ComfyUI

# Install ComfyUI requirements
WORKDIR /workspace/ComfyUI
RUN pip install -r requirements.txt

# Install additional dependencies
RUN pip install runpod

# Install video nodes for ComfyUI
RUN cd custom_nodes && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    git clone https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git

# Copy handler
COPY runpod_handler.py /workspace/

# Set environment
ENV PYTHONPATH=/workspace
ENV COMFYUI_PATH=/workspace/ComfyUI

WORKDIR /workspace

CMD ["python", "runpod_handler.py"]
