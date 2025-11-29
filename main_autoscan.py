import sys
import numpy as np
import kociemba
import pycuber as pc
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import time

face_letters = ['U', 'R', 'F', 'D', 'L', 'B']
face_names = {
    'U': 'Up (White)', 'R': 'Right (Red)', 'F': 'Front (Green)',
    'D': 'Down (Yellow)', 'L': 'Left (Orange)', 'B': 'Back (Blue)'
}
face_colors_gl = {
    'U': (1, 1, 1),        # White
    'R': (1, 0, 0),        # Red
    'F': (0, 0.8, 0),      # Green
    'D': (1, 1, 0),        # Yellow
    'L': (1, 0.5, 0),      # Orange
    'B': (0, 0.3, 1),      # Blue
}
cube_posns = [(x, y, z) for x in [-1, 0, 1] for y in [-1, 0, 1] for z in [-1, 0, 1] if not (x==0 and y==0 and z==0)]


def manual_entry():
    print("Manual Rubik's Cube Entry (faces: U R F D L B / U=White etc.)")
    print("Type 3 letters for each row (e.g. 'URB'), use only U R F D L B\n")
    facelets = []
    for face in face_letters:
        print(f"-- {face_names[face]} face --")
        for i in range(1, 4):
            while True:
                row = input(f"Row {i} (3 letters): ").strip().upper().replace(" ", "")
                if len(row) == 3 and all(c in face_letters for c in row):
                    facelets.extend(row)
                    break
                else:
                    print("Error: Enter exactly 3 of U, R, F, D, L, B.")
    return ''.join(facelets)

def stickers_to_pycuber_text(stickers):
    out = ""
    idx = 0
    for face in face_letters:
        out += f"{face}: "
        out += ' '.join(stickers[idx:idx+9])
        out += "\n"
        idx += 9
    return out

def build_sticker_map(cube):
    # Returns a map: (x, y, z, face) -> color_letter, reflecting current state of the physical cube
    letter_map = {}
    face_order = ['U', 'R', 'F', 'D', 'L', 'B']
    pos_map = {
        'U': lambda i, j: (j-1, 1, -i+1, 'U'),
        'D': lambda i, j: (j-1, -1, i-1, 'D'),
        'F': lambda i, j: (j-1, -i+1, 1, 'F'),
        'B': lambda i, j: (-j+1, -i+1, -1, 'B'),
        'R': lambda i, j: (1, -i+1, -j+1, 'R'),
        'L': lambda i, j: (-1, -i+1, j-1, 'L')
    }
    cstr = str(cube)
    lines = [line for line in cstr.strip().splitlines() if ':' in line]
    for f, line in zip(face_order, lines):
        if ':' in line:
            entries = line.split(':', 1)[1].split()
            for k in range(9):
                i, j = divmod(k, 3)
                pos = pos_map[f](i, j)
                try:
                    letter_map[pos] = entries[k]
                except IndexError:
                    letter_map[pos] = f
    return letter_map

def draw_sticker_face(x, y, z, face, color, sz=0.92):
    """ Draw a single sticker (colored quad) on one face of a cubie."""
    normal_vectors = {
        'U': (0, 1, 0), 'D': (0, -1, 0),
        'F': (0, 0, 1), 'B': (0, 0, -1),
        'R': (1, 0, 0), 'L': (-1, 0, 0)
    }
    normal = normal_vectors[face]
    offset = sz * 0.54
    sticker = sz * 0.78
    glColor3fv(color)
    glBegin(GL_QUADS)
    if face in 'UD':
        u = normal[1]
        for dx, dz in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
            glVertex3f(x + dx*sticker/2, y + u*offset, z + dz*sticker/2)
    elif face in 'FB':
        w = normal[2]
        for dx, dy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
            glVertex3f(x + dx*sticker/2, y + dy*sticker/2, z + w*offset)
    elif face in 'RL':
        v = normal[0]
        for dy, dz in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
            glVertex3f(x + v*offset, y + dy*sticker/2, z + dz*sticker/2)
    glEnd()

def draw_cubie(x, y, z, stickers, sz=0.92):
    # Main black cubie body (drawn as a box, more realistic feel)
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(0.98, 0.98, 0.98)
    glColor3fv((0.12, 0.12, 0.12))
    glBegin(GL_QUADS)
    half = sz/2
    # 6 faces of the cube
    # Front/Back
    for dz in [-half, half]:
        glVertex3f(-half, -half, dz)
        glVertex3f( half, -half, dz)
        glVertex3f( half,  half, dz)
        glVertex3f(-half,  half, dz)
    # Left/Right
    for dx in [-half, half]:
        glVertex3f(dx, -half, -half)
        glVertex3f(dx, -half, half)
        glVertex3f(dx, half, half)
        glVertex3f(dx, half, -half)
    # Top/Bottom
    for dy in [-half, half]:
        glVertex3f(-half, dy, -half)
        glVertex3f( half, dy, -half)
        glVertex3f( half, dy, half)
        glVertex3f(-half, dy, half)
    glEnd()
    # Draw colored stickers
    for face in ['U', 'D', 'F', 'B', 'R', 'L']:
        # Only draw stickers if this is a surface face
        on = ((face == 'U' and y == 1) or (face == 'D' and y == -1) or
              (face == 'F' and z == 1) or (face == 'B' and z == -1) or
              (face == 'R' and x == 1) or (face == 'L' and x == -1))
        if on:
            letter = stickers.get((x, y, z, face), face)
            color = face_colors_gl.get(letter, (1,1,1))
            draw_sticker_face(0, 0, 0, face, color, sz)
    glPopMatrix()

def draw_arrow(face, cw=True, length=2):
    pos = {'U': (0, +1.8, 0), 'D': (0, -1.8, 0), 'F': (0, 0, +1.8),
           'B': (0, 0, -1.8), 'R': (+1.8, 0, 0), 'L': (-1.8, 0, 0)}
    cx, cy, cz = pos[face]
    glPushMatrix()
    glTranslatef(cx, cy, cz)
    glColor3f(1, 1, 0)
    glLineWidth(5)
    glBegin(GL_LINE_STRIP)
    tvals = np.linspace(0, 2*np.pi*0.7, 36)
    use_t = tvals if cw else -tvals
    for t in use_t:
        glVertex3f(np.cos(t)*0.7, np.sin(t)*0.7, 0)
    glEnd()
    glBegin(GL_TRIANGLES)
    a = 0.0
    base = (np.cos(a)*0.7, np.sin(a)*0.7, 0)
    tipL = (np.cos(a+0.21)*1.05, np.sin(a+0.21)*1.05, 0)
    tipR = (np.cos(a-0.21)*1.05, np.sin(a-0.21)*1.05, 0)
    glVertex3f(*base)
    glVertex3f(*tipL)
    glVertex3f(*tipR)
    glEnd()
    glPopMatrix()

def main():
    facelets = manual_entry()
    if len(facelets) != 54 or not all(c in face_letters for c in facelets):
        print("Input error: must be 54 letters (U R F D L B)")
        sys.exit(1)
    try:
        solution = kociemba.solve(facelets)
        moves = solution.strip().split()
        print("\nOptimal solution moves:\n" + solution)
    except Exception as e:
        print("Solver failed:", e)
        return

    pycuber_text = stickers_to_pycuber_text(facelets)
    cube = pc.Cube(pc.Cubie(pycuber_text))

    pygame.init()
    display = (900, 700)
    screen = pygame.display.set_mode(display, DOUBLEBUF|OPENGL)
    glEnable(GL_DEPTH_TEST)
    gluPerspective(45, (display[0]/display[1]), 0.1, 40.0)
    glTranslatef(0, 0, -10)
    glClearColor(0.06, 0.06, 0.06, 1.0)  # dark background for realism

    cam_rot = [30, -45]
    move_idx = 0
    animating = True  # start animation automatically
    animation_angle = 0
    next_move = moves[0] if moves else None
    last_anim_time = time.time()
    dragging = False
    lastpos = None

    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit(); sys.exit()
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE or event.key == ord('q'):
                    pygame.quit(); sys.exit()
                elif event.key == K_SPACE:
                    if move_idx < len(moves):
                        cube(moves[move_idx])  # actually perform that move
                        move_idx += 1
                        next_move = moves[move_idx] if move_idx < len(moves) else None
                        animation_angle = 0
                        animating = True if next_move else False
                        last_anim_time = time.time()
            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                dragging = True
                lastpos = pygame.mouse.get_pos()
            elif event.type == MOUSEBUTTONUP and event.button == 1:
                dragging = False
            elif event.type == MOUSEMOTION and dragging:
                curr = pygame.mouse.get_pos()
                dx = curr[0]-lastpos[0]
                dy = curr[1]-lastpos[1]
                cam_rot[0] += dy*0.5
                cam_rot[1] += dx*0.5
                lastpos = curr

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glPushMatrix()
        glRotatef(cam_rot[0], 1, 0, 0)
        glRotatef(cam_rot[1], 0, 1, 0)

        stickers_map = build_sticker_map(cube)  # dynamically reflects the real state
        for x, y, z in cube_posns:
            glPushMatrix()
            # Animate current move's layer if animating
            if animating and next_move:
                face = next_move[0]
                prime = "'" in next_move
                layer = None
                if face == 'R' and x == 1: layer = 'R'
                if face == 'L' and x == -1: layer = 'L'
                if face == 'U' and y == 1: layer = 'U'
                if face == 'D' and y == -1: layer = 'D'
                if face == 'F' and z == 1: layer = 'F'
                if face == 'B' and z == -1: layer = 'B'
                angle = animation_angle if not prime else -animation_angle
                if layer:
                    if layer in ['R', 'L']:
                        glRotatef(angle, 1,0,0)
                    elif layer in ['U', 'D']:
                        glRotatef(angle, 0,1,0)
                    elif layer in ['F', 'B']:
                        glRotatef(angle, 0,0,1)
            draw_cubie(x, y, z, stickers_map)
            glPopMatrix()
        if next_move:
            draw_arrow(next_move[0], cw=not ("'" in next_move))
        glPopMatrix()
        pygame.display.flip()

        # Animate/rotate then pause; user presses space to advance (just like a real solver)
        if animating and next_move:
            now = time.time()
            animation_angle += 6
            if animation_angle >= 90:
                animation_angle = 0
                if now - last_anim_time < 1:
                    pygame.time.wait(int((1 - (now - last_anim_time)) * 1000))
                last_anim_time = time.time()
        pygame.time.wait(16)

if __name__ == "__main__":
    main()
