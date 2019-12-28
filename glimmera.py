#!/usr/bin/env python

# glimmera

#    Copyright (c) 2006 Dan Wills.
#
#    This file is made from part of 'Motion Graphics in Python' (mgpy) by Simon Yuill.
#
#    'glimmera' is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2.
#
#    'Motion Graphics in Python' is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with 'glimmera'; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
__description__

Texture play using Pygame and OpenGL.

__info__


This uses the Pygame library:

http://www.pygame.org

also pyOpenGL

@author:    Dan Wills
@copyright:    2008 Dan Wills
@license:    GNU GPL version 2
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import random
import math
import os
import colorsys
import time

# CONSTANTS

width = 1024
height = 1024

#width = 1920
#height = 1200

bgColour = ( 0, 0, 0 )  # black background
imageFormat = "RGBA"
fileFormat = "PNG"
renderFiles = 'renderframes'
animName = 'glimmera'

# FUNCTIONS
# hermite smoothstep

def smoothstep( x, smooth_min, smooth_max ) :
    
    lx = 0.0
    
    if smooth_max > smooth_min :
        lx = float( x - smooth_min ) / float( smooth_max - smooth_min )
        
    elif smooth_min > smooth_max :
        lx = float( x - smooth_max ) / float( smooth_min - smooth_max )
        
    else : 
        # smooth_max must be equal to smooth_min
        lx = float( x > smooth_min )
    
    # standard hermite
    
    if x >= smooth_max :
        return 1.0
    elif x <= smooth_min :
        return 0.0
    else :
        return -2 * lx * lx * lx + 3 * lx * lx

# little helper for visualising float values with stars

def getFloatAsStarsStr( float_value, star_white_point, num_stars_at_white_point ) :
    
    scaledFloat = float_value
    
    if star_white_point != 0 :
        scaledFloat /= star_white_point
    
    scaledFloat = min( 1.0, max( 0.0, scaledFloat ) )
    numStars = int( scaledFloat * num_stars_at_white_point )
    star = "*" * numStars
    return star

def loadTextureGL( texture_files ) :
    gl_textures = glGenTextures( len( texture_files ) )
    textureID = 0
    
    for textureFile in texture_files:
        textureSurface = pygame.image.load( textureFile )
        textureData = pygame.image.tostring( textureSurface, "RGBX", 1 )
        glBindTexture( GL_TEXTURE_2D, gl_textures[ textureID ] )
        glTexImage2D( GL_TEXTURE_2D, 0, GL_RGBA, textureSurface.get_width(),
                      textureSurface.get_height(), 0, GL_RGBA, GL_UNSIGNED_BYTE, textureData )
        glTexParameterf( GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR )
        glTexParameterf( GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR )
        textureID += 1
    return gl_textures

def getShutter( pos, fade_width, minimum ) :
    shUp = smoothstep( pos, 0, fade_width )
    shDown = 1.0 - smoothstep( pos, 1.0 - fade_width, 1.0 )
    
    # try to avoid wasteage factor
    return ( shUp * shDown * (1.0 - minimum) ) + minimum

def getShutterSum( shutter_steps, shutter_fade_width ) :
    shutter_sum = 0
    for i in range( shutter_steps ) :
        shutterPos = float( i ) / max( 1.0, float( shutter_steps - 1 ) )
        sh = getShutter( shutterPos, shutter_fade_width, 0.001 )
        shutter_sum += sh
    return shutter_sum

def getOffsetWave( frame_number, shutter_offset, offset_wave_amps, offset_wave_freqs ) :
    xsine = math.sin( (frame_number + shutter_offset) * offset_wave_freqs[ 0 ] ) * offset_wave_amps[ 0 ]
    ysine = math.cos( (frame_number + shutter_offset) * offset_wave_freqs[ 1 ] ) * offset_wave_amps[ 0 ]
    return [ xsine, ysine ]


# noinspection PyShadowingNames
def drawFrame( texture, frame_number, freq, shutter_length, shutter_fade_width,
               shutter_steps, shutter_sum, exposure, offset, hue_freq, scale_freq,
               offset_freq, rotfreq, offset_wave_amps, offset_wave_freqs ):
    
    # consider replacing this with something that fills with transparent black, to fake up a bit more trail
    glClear( GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT )
    glBindTexture( GL_TEXTURE_2D, texture )
    
    for i in range( shutter_steps ) :
        shutter_pos = float( i ) / max( 1.0, float( shutter_steps - 1 ) )
        sh = getShutter( shutter_pos, shutter_fade_width, 0.001 )
        shutter_norm = sh / shutter_sum * exposure
        shutter_offset = (shutter_pos - 0.5) * shutter_length
        offset_wave = getOffsetWave( frame_number, shutter_offset,
                                                        offset_wave_amps, offset_wave_freqs )
        offset_with_wave = [ offs + wav for offs, wav in zip( offset, offset_wave ) ]
        drawPoly( frame_number * freq + shutter_offset, shutter_norm,
                  offset_with_wave, hue_freq * freq, scale_freq * freq,
                  offset_freq * freq, rotfreq * freq )
        
    pygame.display.flip()

def rotate2d( vec, angle_radians ) :
    cos_angle = math.cos( angle_radians )
    sin_angle = math.sin( angle_radians )
    return [ vec[0] * cos_angle - vec[1] * sin_angle,
             vec[0] * sin_angle + vec[1] * cos_angle ]

# noinspection PyPep8,PyPep8,PyPep8,PyShadowingNames
def drawPoly( frame_number, alpha, offset, hue_freq, scale_freq, offset_freq, rot_freq ) :
    
    rquad = frame_number * 5.6
    glLoadIdentity()
    glTranslatef(0.0, 0.0, -6.0)
    zrot = math.sin( rquad / 996.3 ) * 9492.0 * rot_freq
    glRotatef( zrot, 0.0, 0.0, 1.0 )
    
    glBegin( GL_QUADS )    
        
    hue = (rquad * hue_freq) % 1.0
    if hue < 0 :
        hue += 1.0
    hueramp = colorsys.hsv_to_rgb( hue, 1.0, 1.0 )
    
    if hueramp :
        glColor4f( hueramp[0], hueramp[1], hueramp[2], alpha )
    else :
        glColor4f( 1, 1, 1, alpha )
    
    poly_size = math.sin( rquad / 666.3 * scale_freq ) * 5.0
    
    offsvec2d = [ offset[0], offset[1] ]
    rotate2d( offsvec2d, math.radians( frame_number * offset_freq ) )

    # noinspection PyPep8
    glTexCoord2f(0.0, 0.0) ; glVertex3f( poly_size + offsvec2d[0], poly_size + offsvec2d[1], 0.0) # Bottom Left Of The Texture and Quad
    glTexCoord2f(1.0, 0.0) ; glVertex3f(-poly_size + offsvec2d[0], poly_size + offsvec2d[1], 0.0) # Bottom Right Of The Texture and Quad
    glTexCoord2f(1.0, 1.0) ; glVertex3f(-poly_size + offsvec2d[0],-poly_size + offsvec2d[1], 0.0) # Top Right Of The Texture and Quad
    glTexCoord2f(0.0, 1.0) ; glVertex3f( poly_size + offsvec2d[0],-poly_size + offsvec2d[1], 0.0) # Top Left Of The Texture and Quad
    
    glEnd()
    
    
def writeFrame( write_screen, write_frameNumber ):
    """
    Writes frame image to file.
    """
    # format number with zero padding: 001, 002, etc
    fileNumber = str(write_frameNumber).zfill( 4 )
    # create filename for frame
    # frameFilename1 = '%s/%s_%s.tga' % (renderFiles, animName, fileNumber)
    frameFilename2 = '%s/%s_%s.%s' % (renderFiles, animName, fileNumber, fileFormat.lower())
    
    # write file
    print( "writing image file: " + str( frameFilename2 ) )
    pygame.image.save( write_screen, frameFilename2 )
    # pygame.image.save(write_screen, frameFilename1)
    
    # convert and write again
    # image = Image.open( frameFilename1 )
        
    # image.save( frameFilename2, fileFormat )

#######################
# UTILITY FUNCTIONS
#######################

def randomColour( col_min=0, col_max=255 ) :

    """
    Returns a random colour.
    """
    if col_min < 0 :
        col_min = 0

    if col_max > 255 :
        col_max = 255
    red = random.randint(col_min, col_max)
    green = random.randint(col_min, col_max)
    blue = random.randint(col_min, col_max)
    return red, green, blue
    

def resizeGL( scrWidth, scrHeight ) :
    if scrHeight == 0 :
        scrHeight = 1
    glViewport( 0, 0, scrWidth, scrHeight )
    glMatrixMode( GL_PROJECTION )
    glLoadIdentity()
    gluPerspective( 45, 1.0 * scrWidth / scrHeight, 0.1, 100.0 )
    glMatrixMode( GL_MODELVIEW )
    glLoadIdentity()


def initGL() :
    glEnable( GL_TEXTURE_2D )
    glShadeModel( GL_SMOOTH )
    glClearColor( 0.0, 0.0, 0.0, 0.0 )
    glClearDepth( 1.0 )
    # glEnable( GL_DEPTH_TEST )
    glDisable( GL_DEPTH_TEST )
    glEnable( GL_BLEND )
    glDepthFunc( GL_LEQUAL)
    glHint( GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST )
    
    glEnable( GL_BLEND )
    glBlendFunc( GL_SRC_ALPHA, GL_ONE )
    
#######################
# MAIN
#######################
if __name__ == '__main__' :

    verbose = False

    # get tex names
    texpath = "textures/"
    texlist = os.listdir( texpath )
    txxlist = [ texpath + t for t in texlist ]
    txlist = []
    
    for txx in txxlist :
        if os.path.isfile( txx ) :
            txlist.append( txx )

    if verbose :
        print( "texlist: " + str( txlist ) )

    fullscreen = True

    video_flags = OPENGL | DOUBLEBUF
    video_flags_fullscreen = video_flags | FULLSCREEN
    
    pygame.init()
    
    # turn ON ANTIALIASING! :D
    pygame.display.gl_set_attribute( pygame.locals.GL_MULTISAMPLEBUFFERS, 1 )
    
    vflags = video_flags

    if fullscreen :
        vflags = video_flags_fullscreen
    
    screen = pygame.display.set_mode( ( width, height ), vflags )
    
    pygame.display.set_caption( animName )
    resizeGL( width, height )
    
    initGL()
    textures = loadTextureGL( txlist )
    
    # tell the user how many frames are going to be rendered
    # print( "rendering %d frames ..." % frames )
    if verbose :
        print( "INIT finished" )
    # create a loop and draw the animation frames
    # start endless loop
    
    done = False
    recording = False
    frame_number = 0
    recorded_frame_number = 0

    selected_tex = 0
    shutter_samples = 260
    shutter_length = 8.0
    exposure = 1.5
    offset = [ -0.57, 1.08 ]
    offset_wave_amps = [ 0.4, 0.6 ]
    offset_wave_freqs = [ 0.027, 0.013 ]
    freq = 0.115
    hueFreq = 0.4
    # phasepeed is in seconds
    phase_speed = 0.8
    offset_freq = 0.00633
    scale_freq = 114.0
    rot_freq = 2.536
    shutter_sum = getShutterSum( shutter_samples, 0.5 )
    last_time = time.time( )
    
    while not done :
        # draw frame
        
        stex = selected_tex % len( textures )
        if stex < 0 :
            stex = len( textures ) - 1
        
        texture = textures[ stex ]
        drawFrame( texture, frame_number, freq, shutter_length, 0.5,
                   shutter_samples, shutter_sum, exposure, offset,
                   hueFreq, scale_freq, offset_freq, rot_freq,
                   offset_wave_amps, offset_wave_freqs )

        frame_number += 1
        # save frame
        if recording:
            print( "Saving frame: " + str( recorded_frame_number ) )
            writeFrame( screen, recorded_frame_number )
            recorded_frame_number += 1
        # pause before next frame
        # time.sleep(0.1)
        
        newTime = time.time()
        timeDiff = (newTime - last_time)
        # if verbose :
        #   print( "FPS:" + str( 1.0 / timeDiff ) )
        last_time = newTime
        # Event Handling:
        events = pygame.event.get( )

        # print( events )

        for e in events :
            if e.type == QUIT :
                done = True
                break
            elif e.type == KEYDOWN:
                if e.key == K_RIGHT:
                    selected_tex += 1
                    if verbose :
                        print( "Switched to next texture (number %d)" % selected_tex )
                elif e.key == K_LEFT:
                    selected_tex -= 1
                    if verbose :
                        print( "Switched to previous texture (number %d)" % selected_tex )
                    
                elif e.key == K_PAGEUP :
                    if pygame.key.get_mods() & KMOD_CTRL :
                        shutter_samples *= 2
                        if verbose :
                            print( "Doubled shutter samples: " + str( shutter_samples ) )
                    else :
                        shutter_samples += 1
                        if verbose :
                            print( "Increased shutter samples: " + str( shutter_samples ) )
                    # recalc normalization
                    shutter_sum = getShutterSum( shutter_samples, 0.5 )

                elif e.key == K_PAGEDOWN :
                    if pygame.key.get_mods() & KMOD_CTRL :
                        shutter_samples /= 2
                    else :
                        shutter_samples -= 1
                    shutter_samples = max( 1, shutter_samples )
                    shutter_sum = getShutterSum( shutter_samples, 0.5 )

                    if verbose :
                        print( "Reduced shutter samples: " + str( shutter_samples ) )
                    
                    # recalc normalization
                elif e.key == K_HOME :
                    if pygame.key.get_mods( ) & KMOD_CTRL :
                        shutter_length *= 2.0
                        if verbose :
                            print( "Doubled shutter length: " + str( shutter_length ) )
                    else :
                        shutter_length += 1.0
                        if verbose :
                            print( "Incremented shutter length: " + str( shutter_length ) )
                    
                elif e.key == K_END :
                    if pygame.key.get_mods( ) & KMOD_CTRL :
                        shutter_length *= 0.5
                        if verbose :
                            print( "Halved shutter length: " + str( shutter_length ) )
                    else :
                        shutter_length -= 1.0
                        if verbose :
                            print( "Decremented shutter length: " + str( shutter_length ) )
                    
                elif e.key == K_INSERT :
                    exposure *= 1.1
                    if verbose :
                        print( "Exposure up to: " + str( exposure ) )
                    
                elif e.key == K_DELETE :
                    exposure *= 0.9
                    if verbose :
                        print( "Exposure down to: " + str( exposure ) )
                    
                elif e.key == K_LEFTBRACKET :
                    freq *= 0.8
                    if verbose :
                        print( "Base frequency down to: " + str( freq ) )
                    
                elif e.key == K_RIGHTBRACKET :
                    freq *= 1.2
                    if verbose :
                        print( "Base frequency up to: " + str( freq ) )
                
                elif e.key == K_COMMA :
                    hueFreq *= 0.8
                    if verbose :
                        print( "Hue frequency down to: " + str( hueFreq ) )
                    
                elif e.key == K_PERIOD :
                    hueFreq *= 1.2
                    if verbose :
                        print( "Hue frequency up to: " + str( hueFreq ) )
                
                elif e.key == K_SEMICOLON:
                    offset_freq *= 0.8
                    if verbose :
                        print( "Offset frequency down to: " + str( offset_freq ) )
                    
                elif e.key == K_QUOTE :
                    offset_freq *= 1.2
                    if verbose :
                        print( "Offset frequency up to: " + str( offset_freq ) )
                
                elif e.key == K_7:
                    rot_freq *= 0.8
                    if verbose :
                        print( "Rotate frequency down to: " + str( rot_freq ) )
                
                elif e.key == K_8:
                    rot_freq *= 1.2
                    if verbose :
                        print( "Rotate frequency up to: " + str( rot_freq ) )
                    
                elif e.key == K_9:
                    scale_freq *= 0.8
                    if verbose :
                        print( "Scale frequency down to: " + str( scale_freq ) )
                    
                elif e.key == K_0 :
                    scale_freq *= 1.2
                    if verbose :
                        print( "Scale frequency up to: " + str( scale_freq ) )

                elif e.key == K_q :
                    if pygame.key.get_mods( ) & KMOD_CTRL :
                        if verbose :
                            print( "Quit with Ctrl-Q" )
                        done = True
                        break

                elif e.key == K_EQUALS :
                    
                    shutter_length = 7.0
                    # exposure = 1.5
                    offset = [ -1.57, 3.08 ]
                    freq = 0.3
                    hueFreq = 0.082176
                    # phaseSpeed is in seconds
                    phase_speed = 0.8
                    offset_freq = 0.00633
                    scale_freq = 114.0
                    rot_freq = 0.49152

                    if verbose :
                        print( "Freq and offsets reset" )
                
                elif e.key == K_MINUS :
                    freq = --freq
                    if verbose :
                        print( "Freq reversed" )
                    
                elif e.key == K_ESCAPE:
                    if verbose :
                        print( "User pressed escape, exiting.." )
                    done = True
                    break
                    
                elif e.key == K_SPACE:
                    # toggle recording on and off
                    recording = not recording
                    # inform user about recording
                    if recording:
                        # recordedFrameNumber = 0
                        if verbose :
                            print( "Recording frames ...." )
                    else:
                        # print( "%d frames recorded." % recordedFrameNumber )
                        if verbose :
                            print( "Recording stopped ...." )
                        
                elif e.key == K_RETURN:
                    if verbose :
                        print( "Enter pressed, toggling fullscreen to: " + str( not fullscreen) )

                    if fullscreen:
                        fullscreen = False
                        vflags = video_flags
                    else :
                        vflags = video_flags_fullscreen
                        fullscreen = True
                    
                    screen = pygame.display.set_mode( ( width, height ), vflags )
                    pygame.display.set_caption( animName )
                    resizeGL( width, height )
                    initGL()
                    textures = loadTextureGL( txlist )
                    
            elif e.type == MOUSEMOTION:
                # print( "mouse motion, pos: " + str( e.pos ) + " rel: " + str( e.rel ) + " buttons: " + str( e.buttons ) )
                if e.buttons[0] :
                    offset[0] += e.rel[0] / 100.0
                    offset[1] += e.rel[1] / 100.0
                    # print( "Offset is now: " + str( offset ) )
                if e.buttons[1] :
                    offset[0] = 0
                    offset[1] = 0
                    # print( "Offset is ZERO" )
                if e.buttons[2] :
                    offset[0] = ( ( e.pos[0] / float( width ) ) - 0.5 ) * -10
                    offset[1] = ( ( e.pos[1] / float( height ) ) - 0.5 ) * -10
                    # print( "Offset is now: " + str( offset ) )
                            
    # tell the user we have finished
    if verbose :
        print( "%d frames saved." % recorded_frame_number )
