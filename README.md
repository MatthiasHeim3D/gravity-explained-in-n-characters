# Gravity Explained in *n* Characters

![Expanding and shrinking gravity explanation text](./gravity_example.gif)

A LLM experiment explaining the theory of gravity in varying lengths, depending on the size of a resizable text box. As you adjust the box, the application estimates the number of characters that can fit and displays an explanation of gravity tailored to that character count.

## Why

Large language models have an incredible ability to stretch and squash language — They are able to compress vast concepts into bite-sized summaries, or expand simple ideas into much more detailed explanations. This project aims to visualize that linguistic elasticity by dynamically adjusting explanations of a topic, in this case gravity, to fit a given character limit.

## Demo

[Live Demo Link](https://matthiasheim3d.github.io/gravity-explained-in-n-characters/)

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/your-username/your-repo-name.git
   cd your-repo-name
   ```

2. **Set Up the Backend**

   - Ensure you have Python 3 installed.
   - Install required Python packages:

     ```bash
     pip install openai
     pip install matplotlib
     ```

3. **Obtain OpenAI API Key**

   - Sign up on [OpenAI](https://openai.com/) to get an API key.
   - Save your API key in a file named `api_key.txt` in the project root directory.

4. **Generate the Lookup Table**

   Run the `WordGenerator.py` script to generate explanations:

   ```bash
   python WordGenerator.py
   ```

   Then, convert the lookup table to JavaScript format:

   ```bash
   python dump_list_to_javascript.py
   ```

5. **Change prompt**

   To create your own version, change the generation prompt in WordGenerator.py 

## Usage

1. **Open the Application**

   Open `index.html` in your web browser.

2. **Interact**

   - Resize the text box by dragging any edge or corner, with a mouse or by touch.
   - The explanation updates to fit the new size.
   - The character count is displayed in the header.

## Front-end dependency

Text is measured and laid out with [Pretext](https://github.com/chenglou/pretext). A pinned browser bundle is committed in `vendor/`, so `index.html` also works when opened directly. To rebuild that bundle after changing the dependency version:

```bash
npm install
npm run build:pretext
```
