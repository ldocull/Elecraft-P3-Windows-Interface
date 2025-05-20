# Elecraft-P3-Windows-Interface
This application provides point-and-click / scroll-wheel control of frequency and span. 
This application was designed for Windows for use with the [Elecraft P3](https://ftp.elecraft.com/P3/Manuals%20Downloads/E740152%20P3%20Owner%27s%20man%20Rev%20H1.pdf) with the [SVG add-on](https://ftp.elecraft.com/P3/Manuals%20Downloads/E740170%20P3%20SVGA%20Option%20Rev%20E.pdf) and a video capture device [like this one](https://a.co/d/1YxC9fZ).

![K3P3Capture](https://github.com/user-attachments/assets/77d00512-643e-405d-a93f-32d9a2f5c053)

This script was a co-development with ChatGPT. It can be compiled into an executable by:

    pip install pyinstaller  
    pyinstaller --onefile --windowed K3_P3.py


  This will create:
>       dist/
>           K3_P3.exe
>       build/
>           (temporary build files)
>       K3_P3.spec

      
Your executable will be in the _**dist folder**_.

 - Select video source, comm port and baudrate that is compatible with your setup and click 'Save'.
 - Span selections are 10K, 50K, 100K, and 200K.
 - Dropdowns provided to indicate and control Band and Mode.
 - MKRA, MKRB select a marker that can be moved by clicking on the spectrum or waterfall.
 - QSY changes VFO-A or B, depending on which marker is active.
 - MKR-OFF turns off and active markers.
 - A/B, A>B, SPLIT change the rig VFO state just as the front panel buttons do.     
 - Click in the spectrum or waterfall to change the center frequency.        
 - Roll the mouse-wheel up and down to move the center frequency in small amounts.
 - Stay on Top -- will keep this window on top of others on the screen.
 - EXIT saves the current size, position, and Stay-on-Top status of the window for next time.

73,
WR9R

___
Let us know that this work has been helpful to you.  Any proceeds will be used to offset expenses and further the art. 
[![](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=GLAHSMYYJJJAU&source=url)
