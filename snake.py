from copy import copy
from enum import Enum
from pynput import keyboard
from time import sleep
from typing import Final

import random

class Direction(Enum):
    Up    = 0
    Down  = 1
    Left  = 2
    Right = 3

class Position:
    x:int
    y:int

    def __init__(self, x:int, y:int):
        self.x = x
        self.y = y

    def __hash__(self):
        return hash(self.x) + hash(self.y)

    def __eq__(self, position:"Position"):
        return self.x == position.x and self.y == position.y

class ControlCodes:
    ClearScreen = "\x1b[2J\x1b[1;1H"
    Blink       = "\x1b[5m"
    Reset       = "\x1b[0m"
    RedFG       = "\x1b[91m"
    GreenFG     = "\x1b[92m"
    YellowFG    = "\x1b[93m"
    BlueFG      = "\x1b[94m"
    MagentaFG   = "\x1b[95m"
    CyanFG      = "\x1b[96m"

class Board:
    kEmptySymbol:Final = " "
    kBoarderSize:Final = 1

    width:int
    height:int
    paddedWidth:int
    paddedHeight:int

    grid:list[str]
    emptyIndices:set[int]

    def __init__(self, width, height):
        
        self.width  = width
        self.height = height

        # padding for left/right and top/bottom
        self.paddedWidth  = width  + 2*Board.kBoarderSize
        self.paddedHeight = height + 2*Board.kBoarderSize

        # Initialize grid
        self.grid = []
        self.emptyIndices = set()
        for y in range(self.paddedHeight):
            for x in range(self.paddedWidth):

                symbol = self.GetDefaultSymbol(x, y)
                self.grid.append(symbol)

                if symbol == Board.kEmptySymbol:
                    self.emptyIndices.add(y * self.paddedWidth + x)


    def __str__(self):
        result = ""
        for y in range(self.paddedHeight):
            for x in range(self.paddedWidth):
                result+= self.grid[y * self.paddedWidth + x] 
            
            result+= "\n"

        return result

    def GetDefaultSymbol(self, x:int, y:int) -> str:
        if x < Board.kBoarderSize:
            if y < Board.kBoarderSize:
                # upper left boarder
                return "╔"
        
            if y >= self.height + self.kBoarderSize:
                # lower left boarder
                return "╚"

            # left boarder
            return "║"

        if x >= self.width + self.kBoarderSize:
            if y < Board.kBoarderSize:
                # upper right boarder
                return "╗"

            if y >= self.height + self.kBoarderSize:
                # lower right boarder
                return "╝"

            # right boarder
            return "║"
        
        if y < Board.kBoarderSize or y >= self.height + self.kBoarderSize:
            # top/bottom boarder
            return "═"

        # generic space
        return Board.kEmptySymbol

    def GetSymbol(self, position:Position) -> str:
        return self.grid[self.PositionToIndex(position)]

    def SetSymbol(self, position:Position, symbol:str) -> None:
        index = self.PositionToIndex(position)
        self.grid[index] = symbol
        
        if symbol == Board.kEmptySymbol:
            self.emptyIndices.add(index)
        else:
            self.emptyIndices.discard(index)

    def InBounds(self, position:Position) -> bool:
        return (0 <= position.x < self.width) and (0 <= position.y < self.height)

    def GetEmptyPosition(self) -> Position | None:
        if len(self.emptyIndices) == 0:
            return None

        index = random.choice(list(self.emptyIndices))
        return self.IndexToPosition(index)

    def IndexToPosition(self, index:int) -> Position:
        y = index // self.paddedWidth
        x = index - y * self.paddedWidth
        return Position(x - Board.kBoarderSize, y - Board.kBoarderSize)

    def PositionToIndex(self, position:Position) -> int:
        return (position.y + Board.kBoarderSize) * self.paddedWidth + (position.x + Board.kBoarderSize)



class Snake:
    kBodySymbol:Final = f"{ControlCodes.GreenFG}∗{ControlCodes.Reset}"
    kDeathSymbol:Final = f"{ControlCodes.RedFG}∗{ControlCodes.Reset}"

    board:Board
    direction:Direction
    headIndex:int
    segments:list[Position]

    numSegmentsToGrow:int = 0
    isDead = False


    def __init__(self, board:Board, direction:Direction, position:Position):
        self.board = board
        self.direction = direction
        self.headIndex = 0
        self.segments = [position]

    def Kill(self) -> None:
        self.isDead = True
        headPosition = self.segments[self.headIndex]
        self.board.SetSymbol(headPosition, Snake.kDeathSymbol)

    def GetPosition(self, index:int) -> Position:
        return self.segments[index]

    def Size(self) -> int:
        return len(self.segments)

    def SetSize(self, size) -> None:
        numSegments = len(self.segments)

        if size > numSegments:
            
            # add growth
            self.numSegmentsToGrow = size - numSegments

            # Add segments to head
            headPosition = self.segments[self.headIndex]
            for _ in range(self.numSegmentsToGrow):
                self.segments.insert(self.headIndex, copy(headPosition))

        else:
            numSegmentsToDelete = numSegments - size

            # remove growth
            self.numSegmentsToGrow-= numSegmentsToDelete
            if self.numSegmentsToGrow < 0:
                self.numSegmentsToGrow = 0

            # remove segments from tail
            for _ in range(numSegmentsToDelete):

                # make sure the snake is always at least 1 unit long
                if len(self.segments) == 1:
                    break
                
                tailIndex = self.GetTailIndex()
                tailPosition = self.segments.pop(tailIndex)
                self.board.SetSymbol(tailPosition, Board.kEmptySymbol)
    
                # Note: no need to change head index if we're popping segments off in front of it
                if tailIndex < self.headIndex:
                    self.headIndex-= 1


    def GetTailIndex(self) -> int:
        tailIndex = self.headIndex + 1
        if tailIndex >= len(self.segments):
            return 0
        return tailIndex

    def Move(self) -> tuple[Position, str]:
        """Moves the snake in the direction it was going and returns the new position of its head and the symbol it consumed"""
        
        if self.isDead:
            # Don't do anything.
            return self.segments[self.headIndex], ""

        # get new snake head position
        newHeadPosition = copy(self.segments[self.headIndex])
        match self.direction:
            case Direction.Up:
                newHeadPosition.y-= 1

            case Direction.Down:
                newHeadPosition.y+= 1

            case Direction.Left:
                newHeadPosition.x-= 1

            case Direction.Right:
                newHeadPosition.x+= 1

        # erase snake's tail segment
        tailIndex = self.GetTailIndex()
        if self.numSegmentsToGrow > 0:
            self.numSegmentsToGrow-= 1

        else:        
            tailPosition = self.segments[tailIndex]
            self.board.SetSymbol(tailPosition, Board.kEmptySymbol)

        # replace old snake tail with new head segment
        self.segments[tailIndex] = newHeadPosition
        self.headIndex = tailIndex
        consumedSymbol = self.board.GetSymbol(newHeadPosition)
        self.board.SetSymbol(newHeadPosition, Snake.kBodySymbol)

        return newHeadPosition, consumedSymbol


class Apple:
    game:"Game"
    symbol = f"{ControlCodes.RedFG}O{ControlCodes.Reset}"
    position:Position

    def __init__(self, game:"Game", position:Position):
        self.game = game

        self.position = copy(position)
        self.game.board.SetSymbol(position, self.symbol)


    def SetPosition(self, position:Position) -> None:       
        oldPosition = self.position
        self.game.board.SetSymbol(oldPosition, Board.kEmptySymbol)

        self.position = copy(position)
        self.game.board.SetSymbol(position, self.symbol)

    def Eat(self) -> None:
        self.game.score+= 1
        self.game.snake.SetSize(self.game.snake.Size() + 4)

    def Update(self) -> None:
        pass

class SuperApple(Apple):
    symbol = f"{ControlCodes.CyanFG}S{ControlCodes.Reset}"

    def Eat(self):
        self.game.score+= 10
        self.game.updateInterval*= .9
        self.game.snake.SetSize(self.game.snake.Size() + 3)


class Game:

    board:Board
    snake:Snake

    apples:dict[Position, Apple] = {}

    score:int = 0
    updateInterval = 1/2

    appleClasses = [
        Apple, SuperApple
    ]
    
    def __init__(self, width:int, height:int):
        self.board = Board(width, height)
        self.snake = Snake(
            self.board, 
            Direction.Right, 
            Position(width//2, height//2)
        )

        self.SpawnApple()

    def Draw(self) -> None:
        # clear the screen
        displayStr = ControlCodes.ClearScreen

        # score header
        displayStr+= f"Score: {self.score}\n"

        # board
        displayStr+= str(self.board)
    
        print(displayStr, end="")


    def ProcessInput(self, key:keyboard.Key) -> None:

        # Update Snake direction
        match key:
            case keyboard.Key.up:
                self.snake.direction = Direction.Up

            case keyboard.Key.down:
                self.snake.direction = Direction.Down

            case keyboard.Key.left:
                self.snake.direction = Direction.Left

            case keyboard.Key.right:
                self.snake.direction = Direction.Right


    def GameOver(self, message:str) -> None:
        self.Draw()
        print(f"! GAME OVER !\n~ {message}\n")

    def SpawnApple(self) -> bool:
        applePosition = self.board.GetEmptyPosition()
        if applePosition is None:
            # board has no free space
            return False

        # create a random apple 
        appleClass = random.choice(self.appleClasses)
        self.apples[applePosition] = appleClass(self, applePosition)

        return True


    def Update(self) -> bool:
        """Updates the game state and returns true if the game is still running, or false if the game has ended"""

        snakePosition, consumedSymbol = self.snake.Move()
        
        # check if we hit an apple and eat it
        if snakePosition in self.apples:
            apple = self.apples.pop(snakePosition)
            apple.Eat()
            
            # spawn a new apple
            if not self.SpawnApple():
                self.GameOver("You Win!")

        # check if the snake intersects its body
        if consumedSymbol == Snake.kBodySymbol:
            self.snake.Kill()
            self.GameOver("Ouch!")
            return False

        # check if the snake's head is out of bounds
        if not self.board.InBounds(snakePosition):
            self.snake.Kill()
            self.GameOver("Don't Run Away!")
            return False

        return True



    def Start(self) -> None:

        # install keyboard listener
        keyboardListener = keyboard.Listener(on_press=self.ProcessInput)
        keyboardListener.start()

        while True:
            self.Draw()
            sleep(self.updateInterval)
            if not self.Update():
                break

        keyboardListener.stop()


def GetIntInput(prompt, minVal:int, maxVal:int) -> int:
    while True:
        try:
            value = int(input(f"{prompt}: "))
            if value < minVal or value > maxVal:
                print(f"Please enter an integer between {minVal} and {maxVal}")
            else:
                return value

        except ValueError:
            print(f"Invalid Input!")

def main():

    height = 10
    width = 10

    # width  = GetIntInput("Board Width", 10, 100)
    # height = GetIntInput("Board height", 10, 100)

    game = Game(width, height)
    game.Start()


if __name__ == "__main__":
    main()