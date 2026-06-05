import os
from rembg import remove
from PIL import Image

def process_image():
    input_path = 'Assets/Weapons/swb/scarh/scarh.png'
    
    if os.path.exists(input_path):
        print(f"Processing {input_path}...")
        
        # Open the input image
        input_image = Image.open(input_path)
        
        # Remove the background
        output_image = remove(input_image)
        
        # Flip horizontally
        output_image = output_image.transpose(Image.FLIP_LEFT_RIGHT)
        
        # Save the result, overwriting the original file
        output_image.save(input_path)
        print(f"Saved transparent, flipped version to {input_path}")
    else:
        print(f"File {input_path} not found.")

if __name__ == "__main__":
    process_image()
    print("Done!")
