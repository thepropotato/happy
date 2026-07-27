"""THE SAME BRAIN, TYPED AT INSTEAD OF SPOKEN TO: python -m brain"""

import hands
from brain import model
from brain.model import LLMError
from brain.thinking import Happy


def main():
    happy = Happy()

    print(f"{model.name()} AT {model.url()}, TOOLS: {', '.join(hands.names())}. CTRL+C TO QUIT.\n")

    while True:
        said = input("you: ").strip()

        if not said:
            continue

        print("happy: ", end="", flush=True)

        try:
            for part in happy.say_streaming(said):
                print(part, end="", flush=True)
        except LLMError as problem:  # FIX THE SERVER IN THE OTHER WINDOW AND ASK AGAIN.
            print(problem)

        print("\n")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nBye")
