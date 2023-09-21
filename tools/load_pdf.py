import nltk
# nltk.download('punkt')
from PyPDF2 import PdfReader


def read_pdf(file_path):
    # Open the PDF file in read-binary mode
    with open(file_path, 'rb') as f:
        # Read the PDF file using PyPDF2 library
        pdf = PdfReader(f)
        # Get the number of pages in the PDF file
        num_pages = len(pdf.pages)

        # Initialize an empty list to store the paragraphs
        paragraphs = []

        # Iterate through each page of the PDF file
        for i in range(num_pages):
            # Extract the text from each page and split it into sentences
            text = pdf.pages[i].extract_text().split('\n')
            # Split each sentence into words using NLTK
            sentences = [nltk.word_tokenize(sentence) for sentence in text]
            # Join the sentences to form paragraphs and append them to the list of paragraphs
            paragraphs.extend([' '.join(sentence) for sentence in sentences])

    return paragraphs

def main():
    paragraphs = read_pdf('1.pdf')
    print(f'一共{len(paragraphs)}个paragraph')
    # print(paragraphs)

def main11():
    years = [2022, 2023, 2024, 2025, 2026, 2027, 2030]
    loads = [278, 365, 420, 440, 580, 630, 655]
    total_load = sum(loads)
    max_load = max(loads)
    min_load = min(loads)
    average_load = total_load / len(loads)
    print(
        f"The average power load from {years[0]} to {years[-1]} is {average_load:.1f} MW, with a maximum of {max_load} MW and minimum of {min_load} MW.")

if __name__ == "__main__" :
    main11()