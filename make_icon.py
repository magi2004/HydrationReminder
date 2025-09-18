from PIL import Image

# Create a blue square image (64x64)
img = Image.new('RGB', (64, 64), color='blue')
img.save('icon.ico', format='ICO')

print('icon.ico has been created!') 