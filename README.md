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

Non-improvable part (Pandemic.py scrip) : time increases linearly with the number of particles.

  - Method : Basic Matplotlib (Jupyter)

Improvable part : time increases linearly with the number of subplots (~0.1sec / subplot), and the order of magnitude is
such that the number of particles does not really matter. So, the goal is to decrease the number of subplots.

  - Method : Optimized Matplotlib (Jupyter) -> 3 subplots (maybe we can do better with the use of blit)

Improvable part : Time falls below 0.4sec, as expected, but the program is still not fluid enough.

  - Method : PyQtGraph

Improvable part : This library is much faster than Matplotlib (more dedicated to real real-time display) but time increases linearly with the number of particles. So, the program is fluid for a reasonable number of particles
(8 x 50 for example) but is worse than the Optimized Matplotlib script when trying to reach the goal.

  - Method : PyQtGraph + OpenGL 

Improvable part : It is much faster (x10 the non-improvable part when executing "the goal") because OpenGL takes
avantage of the GPU (unlike PyQtGraph used alone visibly). But problem -> it is difficult to display a graph with title, legend, add annotations because of 3D; find a good scale, moving the camera, etc.

  - Method : Bokeh

Improvable part : Plotting in real time seems to be possible only in server mode (to check). It is pretty fast (less 
than OpenGL though) but there are several graphic bugs occuring when particles turn color.

  - Method : Vispy (vispy.plot)
  
Improvable part : Same bugs as on Bokeh and slower than it by using vispy.plot.

  - Method : Vispy (vispy.canvas + vispy.gloo)
  
Improvable part : Really fast but rendering text with it is tricky (similar to OpenGL : logic since it uses this library).

Conclusion : I combined vispy.canvas/vispy.gloo (for the scatter plots) and pyqtgraph (for the pandemic evolution graph).

-----

For Jupyter scripts : they may not work if you try to run it in a .py script because the "%matplotlib notebook" IPython Magic Command 
is used. In this case, maybe try to use the "matplotlib.animation.FuncAnimation" function.

Most comments are in French.
