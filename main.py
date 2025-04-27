from game.engine import GameEngine

def main():
    # Create and run the game
    game = GameEngine()
    game.run()

if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception as e:
        print("The game crashed with an exception:")
        traceback.print_exc()
        input("Press Enter to exit...")