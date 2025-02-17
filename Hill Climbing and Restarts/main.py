
import random
import time
from evaluators.SimpleSqrtEvaluationFunction3MultiState import SimpleSqrtEvaluationFunction3MultiState
from game.gameState import GameState
from game.physicalGameState import PhysicalGameState
from game.playerAction import PlayerAction
from game.screen import ScreenMicroRTS
from game.unitTypeTable import UnitTypeTable
from playout.simpleMatch import SimpleMatch
from synthesis.ai.Interpreter import Interpreter
from synthesis.baseDSL.mainBase.node import Node
from synthesis.baseDSL.tests.scriptsToy import ScriptsToy
from synthesis.baseDSL.util.control import Control
from synthesis.baseDSL.util.factory_Base import Factory_Base
from synthesis.extent1DSL.neighborhood_functions.neighborhood import Neighborhood

def playout(gs_a, ai0, ai1, player, max_tick, show_screen, assistant_evaluator):
    gs = gs_a.clone()
    ai0.reset()
    ai1.reset()
    if assistant_evaluator!=None: 
        assistant_evaluator.reset()

    if show_screen:
        screen = ScreenMicroRTS(gs)
    show = True
    
    while not gs.gameover() and gs.getTime()<max_tick:
        if assistant_evaluator!=None:
            assistant_evaluator.analysis(gs,player,False)
        if show and show_screen:
                screen.draw()
                time.sleep(0.1) 

        ini_time = time.time()
        try:
            pa0 :  PlayerAction =ai0.getActions(gs,player)
        except Exception as e:
            return 1-player  , -1
        timeP0 = time.time()- ini_time
        
        ini_time = time.time()  
        pa1 = ai1.getActions(gs,1 -player)
        timeP1 = time.time()- ini_time
        
        if timeP0>0.110 and timeP1>0.110:
            return -1,-1
        elif timeP0>0.110 :
            return 1- player,-1
        elif timeP1>0.110:
            return player,-1
        
        if show_screen: show = gs.updateScreen()
            
        gs.issueSafe(pa0)
        gs.issueSafe(pa1)      
        gs.cycle()
    if assistant_evaluator!=None:
        assistant_evaluator.analysis(gs,player,True)
        
    if assistant_evaluator!=None:   

        return gs.winner() ,assistant_evaluator.getValue()
    
    return gs.winner(), 0

def winToScore(player, result):
    if player == result: return 1.0
    if 1 - player == result: return 0.0
    return 0.5

def evaluate(node, target_program, gs, max_tick):
    eval = SimpleSqrtEvaluationFunction3MultiState()
    utt = gs.getUnitTypeTable()
    a1 = Interpreter(gs.getPhysicalGameState(),utt,node)
    score = 0
    
    a2 = Interpreter(gs.getPhysicalGameState(),utt,target_program)
    win, auxiliary_score0 = playout(gs,a1,a2,0,max_tick,False,eval)
    score += winToScore(0, win)
    win, auxiliary_score1 = playout(gs,a1,a2,1,max_tick,False,eval)
    score += winToScore(1, win)
        
    return score/2,(auxiliary_score0+auxiliary_score1)/2

def visualize_game(program_1, program_2):
    utt = UnitTypeTable(2)
    pgs = PhysicalGameState.load(map, utt)
    gs = GameState(pgs, utt)

    symbolic_1 = Interpreter(pgs, utt, program_1)
    symbolic_2 = Interpreter(pgs, utt, program_2)
    
    sm = SimpleMatch()
    win = sm.playout(gs, symbolic_1, symbolic_2, 0, 7000, True)

    print("Winner = ", win[0] + 1)

def search(target_program, neighborhood_function, num_neighbors, max_tick, map):
    utt = UnitTypeTable(2)
    pgs = PhysicalGameState.load(map, utt)
    gs = GameState(pgs, utt)

    prog = ScriptsToy.scriptEmpty() 
    seed_search = prog 
    best_eval, best_auxiliary = evaluate(prog, target_program, gs, max_tick)
    total_number_evaluations = 1  #counting the beginning evaluation in prog as discussed in slack

    temp_eval = best_eval  
    temp_aux = best_auxiliary

    while best_eval != 1:  
        successors = neighborhood_function.get_neighbors(prog, num_neighbors)
        imp = False #to check if improved or not
        
        for c in successors:
            current_eval, current_aux = evaluate(c, target_program, gs, max_tick)
            total_number_evaluations += 1

            if current_eval > best_eval or (current_eval == best_eval and current_aux > best_auxiliary):
                imp = True
                prog = c
                best_eval = current_eval
                best_auxiliary = current_aux
                
            if best_eval == 1:
                return prog, total_number_evaluations

        #Adding restarts
        if imp != True:
            
            if best_eval > temp_eval or (best_eval == temp_eval and best_auxiliary > temp_aux):
                temp_eval = best_eval
                seed_search = prog
                temp_aux = best_auxiliary

            if random.random() < 0.5 and temp_eval > 0: #gives 50% probability
                prog = seed_search
            else:
                prog = ScriptsToy.scriptEmpty() #new

            best_eval, best_auxiliary = evaluate(prog, target_program, gs, max_tick)
            total_number_evaluations += 1

    return prog, total_number_evaluations

if __name__ == "__main__":
    random.seed(42)

    max_tick = 3000
    neighborhood_function = Neighborhood()
    num_neighbors = 20
    map = "./maps/basesWorkers32x32A.xml"
    factory = Factory_Base()

    program_target_1 = ScriptsToy.script7()

    start_time = time.time()
    print('Program 1 to be Defeated')
    print(program_target_1.translate())
    print()
    prog_result, number_evaluations = search(program_target_1, neighborhood_function, num_neighbors, max_tick, map)
    print('Number of evaluations: ', number_evaluations)
    end_time = time.time()
    print('Time required to compute a best response to the first program: ', end_time - start_time)
    visualize_game(prog_result, program_target_1)
    print()

    start_time = time.time()
    program_target_string = "S;For_S;S;S_S;S;S_S;S;C;Build;Barracks;Down;2;S;C;Attack;Closest;S;C;Train;Ranged;Right;15"
    program_target_2 = Control.load(program_target_string, factory)
    print('Program 2 to be Defeated')
    print(program_target_2.translate())
    print()
    prog_result, number_evaluations = search(program_target_2, neighborhood_function, num_neighbors, max_tick, map)
    end_time = time.time()
    print('Time required to compute a best response to the second program: ', end_time - start_time)
    print('Number of evaluations: ', number_evaluations)
    visualize_game(prog_result, program_target_2)
