# Gravity Explained in *n* Characters

![Expanding and shrinking gravity explanation text](./gravity_example.gif)

A LLM experiment explaining the theory of gravity in varying lengths, depending on how much room there is to say it. The text fills a procedurally drawn lake that is sized from the browser window; the application estimates how many characters fit in the water and displays an explanation of gravity tailored to that character count. Apples and stones dropped into the lake displace the text as they fall and settle.

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

   - A short guided run starts by itself: a title, then one line about density per tap.
   - Tap or click anywhere to drop what the current line is about -- enough rocks to
     line the bed, then the fish, then the duck, then up to five apples.
   - Drag anything around, or let it sink; the text flows around whatever is in the water.
   - Resize the browser window to resize the lake. The explanation updates to fit.
   - Start over resets the lake and replays the run.

## Front-end dependency

Text is measured and laid out with [Pretext](https://github.com/chenglou/pretext). A pinned browser bundle is committed in `vendor/`, so `index.html` also works when opened directly. To rebuild that bundle after changing the dependency version:

```bash
npm install
npm run build:pretext
```
