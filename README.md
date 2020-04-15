Simulation of an epidemic in Python

Broadly inspired by the video "Simulating an epidemic" from 3Blue1Brown

Current options :
  - Visual representation of interactions between particles
  - Graph of the evolution of the epidemic in real time (counting susceptible, infected, recovered, dead people)
  - Putting infected people in quarantine zone.
  - World with multi-country mode (-> Pandemic)

-----

Comparison betweeen the "Pandemic simulation" scripts

Goal : Display 8 x 500 particles seamlessly

Non-improvable part executing time is (as expected) always the same; time INCREASES LINEARLY WITH THE NUMBER OF PARTICLES

  - Method : Basic Matplotlib (Jupyter)
Improvable part : time INCREASES LINEARLY WITH THE NUMBER OF SUBPLOTS (~0.1sec / subplot), and the order of magnitude is
such that the number of particles does not really matter. So, the goal is to decrease the number of subplots 
(ideally maximum 3 subplots).

  - Method : Optimized Matplotlib (Jupyter) -> 3 subplots (maybe can do better with the use of blit)
Improvable part : Time falls below 0.4sec, as expected, but the program is still not fluid enough.

  - Method : PyQtGraph
Improvable part : This library is much faster than Matplotlib (more dedicated to real real-time display) but time
INCREASES LINEARLY WITH THE NUMBER OF PARTICLES. So, the program is fluid for a reasonable number of particles
(8 x 50 for example) but is worse than the Optimized Matplotlib script when trying to reach the goal.

  - Method : PyQtGraph + OpenGL 
Improvable part : It is much faster (x10 the non-improvable part when executing "the goal") because OpenGL takes
avantage of a part of the GPU (unlike PyQtGraph used alone). It is still not enough fluid to me but problem comes from 
the non-improvable part, so it seems there is nothing to do more.
Problem -> it is difficult to display a graph with title, legend, add annotations because of 3D; find a good scale,
moving the camera, etc.

  - Method : Vispy
Improvable part : Same bugs as on Bokeh and slower than it by using vispy.plot.

I will try to improve results by using vispy.app.Canvas class instead (take advantage of the GPU through the use of 
shaders, etc...

-----

For Jupyter scripts : they may not work if you try to run it in a .py script because the "%matplotlib notebook" IPython Magic Command 
is used. In this case, maybe try to use the "matplotlib.animation.FuncAnimation" function.

Documentation is in French.
