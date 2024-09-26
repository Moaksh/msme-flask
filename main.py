from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import markdown2
from xhtml2pdf import pisa
import os
import base64
from pymongo import MongoClient
from bson import ObjectId
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
# Replace this with your actual OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Use environment variable for security
client = OpenAI(api_key=OPENAI_API_KEY)

# MongoDB connection
mongo_client = MongoClient(os.getenv("MONGODB_URI"))  # Ensure you have your MongoDB URI in an environment variable
db = mongo_client['your_database_name']  # Replace with your database name
pdf_collection = db['pdf_files']  # Collection to store PDF files

def convert_html_to_pdf(html_string):
    pdf_file = pisa.CreatePDF(html_string)
    return pdf_file.dest.getvalue()

@app.route('/')
def index():
    return jsonify({"Choo Choo": "Welcome to the Flask app 🚅"})

@app.route('/submit', methods=['POST'])
def submit():
    data = request.json
    print(data)
    prompt = (
        f"I am {data['name']}, a {data['age']}-year-old {data['gender']} from {data['town']}, {data['district']}. "
        f"I plan to start a {data['business_type']} business in the {data['sector']} sector. "
        f"{'With my ' + data['educational_qualification'] + ' background, I fall under the ' + data['category'] + ' category.' if data['educational_qualification'] and data['category'] else ''} "
        f"I aim to establish my venture in {data['business_location']}, focusing on {data['business_idea_brief']}. "
        f"{'This is my first business venture.' if data['is_first_business'] == 'Yes' else 'This is not my first business venture.'} "
        f"{'Based on my research, I believe that ' + data['research_summary'] + '.' if data['market_research'] == 'Yes' else ''} "
        f"{'I bring relevant skills and experience to the table, including ' + data['skills_description'] + '.' if data['skills_experience'] == 'Yes' else ''} "
        f"I plan to start the business within {data['timeline']} and intend to invest {data['investment_amount']} in the venture. "
        f"{'My first-year goals include ' + data['goals_description'] + '.' if data['goals_description'] else ''} "
        f"{'Some concerns I have about starting the business are ' + data['concerns_description'] + '.' if data['concerns_description'] else ''} "
        f"Also, use markdown to render the report and mention explicitly that it was prepared for {data['name']}"
        "Make the report extremely detailed, pay attention to detail for all the subsections"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )

        generated_response = ""
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                generated_response += chunk.choices[0].delta.content

        # Generate PDF
        html_text = markdown2.markdown(generated_response)
        pdf_data = convert_html_to_pdf(html_text)

        # Store PDF in MongoDB
        pdf_document = {
            'pdf_file': base64.b64encode(pdf_data).decode('utf-8'),
            'content_type': 'application/pdf'
        }
        result = pdf_collection.insert_one(pdf_document)
        pdf_id = str(result.inserted_id)

        # Create a URL or identifier to access the PDF
        domain = request.host_url.rstrip('/')
        pdf_url = f"{domain}/pdf/{pdf_id}"  # This could be a route to download the PDF
        print(pdf_url)
        return jsonify({'response': generated_response, 'pdf_url': pdf_url})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/pdf/<pdf_id>', methods=['GET'])
def get_pdf(pdf_id):
    pdf_document = pdf_collection.find_one({'_id': ObjectId(pdf_id)})
    if pdf_document:
        pdf_data = base64.b64decode(pdf_document['pdf_file'])
        return pdf_data, 200, {'Content-Type': pdf_document['content_type'], 'Content-Disposition': f'attachment; filename="{pdf_id}.pdf"'}

    return jsonify({'error': 'PDF not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
