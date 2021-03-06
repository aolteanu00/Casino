"""
Session data created by rick and morty game (these will also be deleted upon finishing the game):
- "game_state": Determines which route to use. The possible values (str):
    - "pregame": User did not pay yet, but did select rick and morty as the game he/she wants to play
    - "selecting": The user sees the questionaire, but did not fill it out yet
    - "result": The user has answered the questionaire and the result is shown to the user. At this point, the session
    data created by this Blueprint is deleted and the session["paid"] is set to False
- "images" (list of str): A list of image links for three random rick and morty characters
- "answers" (list of str): A list of names corresponding to each image in order: image[1]'s answer is answer[1]

Session data updated
- "paid": Will be set to False once the game is completed
- "bet_amount": Will be set to 0 once the game is finished
- "current_game" Will be deleted
"""

import random
from flask import Blueprint, session, render_template, redirect, url_for, request
from rickandmorty_game.rickandmorty_game import get_three_random_characters, get_character_image, get_random_character, user_balance_lost_rickandmorty, get_nine_random_characters
from data.database_query import update_balance, get_balance

rickandmorty_game = Blueprint("rickandmorty_game", __name__)

@rickandmorty_game.route("/rickandmorty")
def rickandmorty():
    # Must be logged in to play a game
    if "username" not in session:
        return redirect(url_for("login"))

    # Cannot play multiple games at once
    if "current_game" in session and session["current_game"] != "rickandmorty_game.rickandmorty":
        print("Trying to play Rick and Morty but is already playing " + session["current_game"])
        return redirect(url_for("game"))
    else:
        session["current_game"] = "rickandmorty_game.rickandmorty"
        # If the user is already playing this game and either goes back in history from browser / manually enter url,
        # bring them to the route they are supposed to be on
        if "game_state" in session:
            if session["game_state"] == "selecting":
                return redirect(url_for(".rickandmorty_select"))
            elif session["game_state"] == "result":
                return redirect(url_for("./rickandmorty_result"))
        else:
            print("User is now playing Rick and Morty")
            session["game_state"] = "pregame"

    # Must pay before
    if session["paid"]:
        session["game_state"] = "selecting"
        return redirect(url_for(".rickandmorty_select"))
    else:
        return redirect(url_for("bet"))

@rickandmorty_game.route("/rickandmorty/select")
def rickandmorty_select():
    # Must be logged in to play
    if "username" not in session:
        return redirect(url_for("login"))

    # Make sure the user is playing the pokemon game
    if "current_game" not in session or session["current_game"] != "rickandmorty_game.rickandmorty":
        # User did not select a game or user is playing another game
        return redirect(url_for(".rickandmorty"))

    # Make sure the user is on the right page
    if session["game_state"] != "selecting":
        return redirect(url_for(".rickandmorty"))

    # Prevents user from refreshing the cards on page reload
    if "correct_ans" not in session:
        characters = get_three_random_characters()
        session["correct_ans"] = characters
        session["user_choices"] = characters
    character_images = [get_character_image(name) for name in session["correct_ans"]]
    # List of random filler characters
    if "wrong_ans" not in session:
        wrong_ans = get_nine_random_characters()
        # Check if any value is the answer. Only checks once however but the chances of picking a invalid character is <1%.
        for i in wrong_ans:
            if i in session["correct_ans"]:
                wrong_ans.remove(i)
                wrong_ans.append(get_random_character())
        session["wrong_ans"] = get_nine_random_characters()
    # print(character_images)
    # print(session["wrong_ans"]
    if "correct_ans_index" not in session:
        correct_ans_index = [random.randint(0, 3), random.randint(0, 3), random.randint(0, 3)]
        session["correct_ans_index"] = correct_ans_index
    print(session["correct_ans_index"])
    return render_template("rickandmorty/select.html", correct_ans_index = session["correct_ans_index"], wrong_answers = session["wrong_ans"], answers = session["correct_ans"], character_images = character_images)

@rickandmorty_game.route("/rickandmorty/result", methods=["POST"])
def rickandmorty_result():
    # print(session["correct_ans"])
    # print(request.form["answer"])
    # Must be logged in to play
    if "username" not in session:
        return redirect(url_for("login"))

    # Make sure the user is playing the pokemon game
    if "current_game" not in session or session["current_game"] != "rickandmorty_game.rickandmorty":
        # User did not select a game or user is playing another game
        return redirect(url_for(".rickandmorty"))

    if ("game_state" not in session) or session["game_state"] != "selecting":
        return redirect(url_for(".rickandmorty"))

    if len(request.form) != 3:
        return redirect(url_for(".rickandmorty"))

    session["game_state"] = "result"
    user_ans_1 = request.form["answer"]
    user_ans_2 = request.form["answer1"]
    user_ans_3 = request.form["answer2"]
    user_ans_list = [user_ans_1, user_ans_2, user_ans_3]
    user_change_balance = user_balance_lost_rickandmorty(user_ans_list, session["correct_ans"], session["bet_amount"])
    user_current_balance = get_balance(session["username"])

    bet_amt = session["bet_amount"]
    half_bet_amt = session["bet_amount"] * .5
    if user_change_balance == session["bet_amount"]:
        winner_message = "You broke even!"
        balance_message = f"The {session['bet_amount']} MAWDollars you bet was returned"
        new_balance = user_current_balance + session["bet_amount"]
    elif user_change_balance > session["bet_amount"]:
        winner_message = "You won!"
        # If user won, he/she gets back what was bet and what was won
        new_balance = user_current_balance + user_change_balance
        balance_message = f"You won {user_change_balance} MAWDollars"
    elif user_change_balance == 0:
        winner_message = "You lost"
        new_balance = user_current_balance + user_change_balance
        balance_message = f"You lost {bet_amt} MAWDollars"
    else:
        winner_message = "You lost"
        # If user lost, he/she lost what was bet and what was lost
        new_balance = user_current_balance + user_change_balance
        balance_message = f"You lost {half_bet_amt} MAWDollars"

    print("User old balance: {}\nUser new Balance: {}".format(user_current_balance, new_balance))
    update_balance(session["username"], new_balance)

    correct_answers = session["correct_ans"]
    character_images = [get_character_image(name) for name in session["correct_ans"]]
    del session["game_state"]
    session["paid"] = False
    session["bet_amount"] = 0
    del session["correct_ans"]
    del session["correct_ans_index"]
    del session["wrong_ans"]
    del session["current_game"]

    return render_template("rickandmorty/result.html", winner_message = winner_message, balance_message = balance_message, correct_ans = correct_answers, images = character_images)

@rickandmorty_game.route("/leave-rickandmorty")
def leave_rickandmorty():
    del session["game_state"]
    session["paid"] = False
    session["bet_amount"] = 0
    del session["correct_ans"]
    del session["correct_ans_index"]
    del session["wrong_ans"]
    del session["current_game"]
    return redirect(url_for("game"))

@rickandmorty_game.route("/rickandmorty/instructions")
def rickandmorty_instructions():
    return render_template("rickandmorty/instructions.html");
