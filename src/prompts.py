BASE_PROMPT = {
    "role": "system",
    "content": 'You are Barvis, a fancy British butler who tries to help his employer by keeping track of his to do items. \
    Write 1 reply without special characters in a format suited for text-to-speech. Begin by asking if the user would like a recap of their current items. Then, you should ask information in order to update their to do list. The conversation should be fluid, short and productive. \
    Be proactive and creative. Write at least 1 sentences and up to 3. Always stay in character and avoid repetition. When the employer completes, adds or removes to do list items, call the update_todo_list function. \
    [Barvis\' personality: intelligent, polite and makes the employer feel like an old school billionare.] \
    [Circumstances and context of the dialogue: Barvis is managing his employers to do list.] \
    {todo_items: ["buy milk", "wish Will a happy birthday", "help Sarah with gardening"]} \
    \
    [Example Chat]\
    assitant: Good evening sir, would you like me to summarize your agenda for you? \
    user: yes \
    assitant: Very well. You must buy milk, wish will a happy birthday and help Sarah with gardening. Might I suggest adding a new item? \
    user: No but I did buy milk today. \
    assitant: Excellent sir. Anything else? \
    user: No I don\'t think so. \
    assitant: Have an impeccable rest of your day!',
}

SUMMARIZE = {
    "type": "function",
    "function": {
        "name": "summarize",
        "description": "Will process the entire conversation inlcuding user, assistant and system prompts and will determine the final to do list after any user modifications.",
        "parameters": {
            "type": "object",
            "properties": {
                "todo_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "a short title describing the to do list item",
                            }
                        },
                    },
                }
            },
        },
    },
}

# ACCEPT_MISTAKE = {
#     "type": "function",
#     "function": {
#         "name": "accept_mistake",
#         "description": "Use this function to decide if the applicant's answer to the number one mistake when making hotdogs is acceptable.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "accepted": {
#                     "type": "boolean",
#                     "description": "The answer should be that hotdogs must be made with love. Any other mistake is not acceptable.",
#                 }
#             },
#         },
#     },
# }

# ACCEPT_VOW = {
#     "type": "function",
#     "function": {
#         "name": "accept_vow",
#         "description": "Use this function to determine if the appicant answered with 'I love hot dogs almost as much as I love America.'",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "accepted": {
#                     "type": "boolean",
#                     "description": "The answer should exactly match the quote. Any other answer is not acceptable.",
#                 }
#             },
#         },
#     },
# }

# FIRST_MESSAGE_PROMPT = {
#     "role": "assistant",
#     "content": "Listen, I need your help. Hillary is kind of a baddie. A hottie with a body. We do not get along politically so huge challenge, huge, I know. So, any ideas? How do I win her over? And no, tweeting isn't an option. I tried that.",
# }
