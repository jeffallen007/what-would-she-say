import kagglehub

# Download latest version
path = kagglehub.dataset_download("pierremegret/dialogue-lines-of-the-simpsons")

print("Path to dataset files:", path)