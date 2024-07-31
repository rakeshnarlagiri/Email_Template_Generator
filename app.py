import time
import json
import openai
import streamlit as st
import os

OPENAI_API_KEY = st.sidebar.text_input("OpenAI API Key", type="password")

openai.api_key = OPENAI_API_KEY


def generate_email_auto(variables, product_description, recept_type, tone, no_of_words):
    tone_map = {
        "Professional": "formal and neutral",
        "Casual": "friendly and positive"
    }

    if tone:
        tone = tone_map.get(tone, "informative")  # Default to informative if interest level is u
    prompt = f"""You are an expert email content creator. You have to create an email for various insurance product 
    based on product description and type of email template required which will be given by the user. YOu have to add 
    all possible dynamic fields and map them on the email template with a list of variable names given to you in a 
    json format.

    produce description: {product_description}
    type of recept:{recept_type}
    tone :{tone}
    """
    question = f"""- Do not include a variable in the response JSON if proper mapping is not found in the json file. - 
    In the list of variables the property name refers to the variable name and type refers to the data type of the 
    variable.

    The list of variables are:
    {variables}

    Return only the JSON object.
    the  generated email should not be more than {no_of_words} words.
    Do not include markdown "```" at the start or end.
    DO not include any comments in the response.
    The response should be able to be parsed into a JSON object.
    """

    complete_prompt = f"{prompt}\n\n{question}"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": complete_prompt},
        ],
        max_tokens=500,
        temperature=0.7,
    )

    email = response.choices[0].message['content'].strip()

    return email


def regenerate_email_with_prompt(original_email, user_prompt):
    # Create the prompt for OpenAI to modify the email
    structured_input = (
        f"Here is an email:\n{original_email}\n\n"
        f"Please modify the email according to this prompt: {user_prompt}\n\n"
        f"give the same email content with changes made do not change the whole content"
        f"The response should be able to be parsed into a JSON object."
    )

    # Generate the output using OpenAI API
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": structured_input},
        ],
        max_tokens=500,
        temperature=0.7,
    )

    modified_email = response.choices[0].message['content'].strip()

    return modified_email


def save_to_file(filename, content):
    try:
        with open(filename, "w", encoding="utf-8") as file:
            file.write(content)
        st.success(f"Email content has been saved as {filename}")
    except IOError as e:
        st.error(f"Error saving file: {e}")


with open('variables.json', 'r') as file:
    variable_list = json.load(file)
with open('products.json', 'r') as f:
    product_list = json.load(f)

with open('recept.json', 'r') as f1:
    recept_list = json.load(f1)

st.header("Email Template Generator")
selected_product = st.sidebar.selectbox("Select Product",
                                        [product_set['product_name'] for product_set in product_list])
selected_input = next((input_set for input_set in product_list if input_set['product_name'] == selected_product),
                      None)

recept_type = st.sidebar.selectbox("Sub Product",
                                   [recept_set['recept_type'] for recept_set in recept_list])

selected_recept = next((input_set for input_set in recept_list if input_set['recept_type'] == recept_type),
                       None)

recept_description = selected_recept['recept_description']

tone = st.sidebar.selectbox("Tones", ["Professional", "Casual"])

no_of_words = st.sidebar.text_input("Word Limit")

custom_variables = []
variables = None
if selected_product == "custom":
    with st.sidebar.expander("custom product"):
        product_description = st.sidebar.text_area("product description")
        with st.sidebar.expander("variables"):
            num_custom_vars = st.sidebar.number_input("Number of Variables", min_value=1, max_value=20, step=1)
            for i in range(num_custom_vars):
                var_name = st.sidebar.text_input(f"Variable {i + 1} Name")
                var_value = st.sidebar.text_input(f"Variable {i + 1} Value")
                custom_variables.append({var_name: var_value})

else:
    product_description = selected_input['product_description']
    variables = [variable_set['name'] for variable_set in variable_list]
# with st.sidebar.expander("variables"):
#     all_variables = st.sidebar.write("variables", variables)

if st.sidebar.button("Generate Template", key="generate_email"):
    if no_of_words:
        if selected_product == "custom":
            email_content = generate_email_auto(
                custom_variables,
                product_description,
                recept_description,
                tone,
                no_of_words
            )
        else:
            email_content = generate_email_auto(
                variables,
                product_description,
                recept_description,
                tone,
                no_of_words
            )
        st.session_state.generated_email = json.loads(email_content)
    else:
        st.warning("Enter the words limit in the side bar")
if OPENAI_API_KEY:
    if 'generated_email' in st.session_state:
        generated_email = st.session_state.generated_email

        try:
            string_email_content = f"Subject: {generated_email['subject']}\n\n{generated_email['body']}"
        except KeyError as e:
            st.error(f"Missing key in generated email: {e}")
            string_email_content = ""

        st.subheader("Generated Template")
        st.text_area("Email Content", string_email_content, height=300)

        if st.button("Save Template", key="save_email"):
            timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
            file_name = f"{selected_product}_{timestamp}.txt"
            save_to_file(file_name, string_email_content)

        user_prompt = st.chat_input(placeholder="Enter your prompt to change")

        if user_prompt:
            try:
                modified_email = regenerate_email_with_prompt(generated_email, user_prompt)
                modified_email = json.loads(modified_email)
                modified_email_content = f"Subject: {modified_email['subject']}\n\n{modified_email['body']}"
                st.text_area("Modified Content", modified_email_content, height=400)
            except (KeyError, json.JSONDecodeError) as e:
                st.error(f"Error processing modified email: {e}")
                modified_email_content = ""

            if st.button("Save Template", key="save_modified_email"):
                timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
                file_name = f"{selected_product}_{timestamp}.txt"
                save_to_file(file_name, modified_email_content)
else:
    st.warning("Please Entre OPENAI_API_KEY")
