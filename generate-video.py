import os
import moderngl
import numpy as np
from PIL import Image
import imageio
import math

# === Базовые параметры ===
WIDTH = 1920          # Ширина кадра
HEIGHT = 1080         # Высота кадра
FRAMES = 240         # Количество кадров
FPS = 30             # Частота кадров
OUTPUT_FILE = "MengerSponge.mp4"  # Имя выходного файла
TEMP_DIR = "images"  # Директория для временных изображений

# === Параметры губки Менгера ===
SPONGE_SIZE = 4       # Размер губки Менгера
SPONGE_LEVEL = 4      # Уровень рекурсии губки Менгера

# === Параметры камеры ===
CAMERA_DISTANCE = 10   # Расстояние камеры от центра

# === Параметры освещения ===
LIGHT_POSITIONS = [
    [CAMERA_DISTANCE, 0, 0],    # Свет справа
    [-CAMERA_DISTANCE, 0, 0],   # Свет слева
    [0, CAMERA_DISTANCE, 0],    # Свет сверху
    [0, -CAMERA_DISTANCE, 0],   # Свет снизу
    [0, 0, CAMERA_DISTANCE],    # Свет спереди
    [0, 0, -CAMERA_DISTANCE],   # Свет сзади
]
LIGHT_INTENSITY = 0.6           # Интенсивность освещения

# === Параметры вращения ===
ROTATION_AXIS = [0, 1, 1]   # Ось вращения
ROTATION_SPEED = 2 * math.pi / FRAMES  # Скорость вращения (угол на кадр)

# === Параметры цвета ===
OBJECT_COLOR = [255 / 255, 215 / 255, 0 / 255]  # Цвет объекта (RGB)
AMBIENT_COLOR = [0.2, 0.2, 0.3]                 # Цвет фонового освещения (RGB)
BACKGROUND_COLOR = [221 / 255, 221 / 255, 221 / 255]  # Цвет фона
TRANSPARENCY = 1.0              # Прозрачность объекта (1.0 = непрозрачный)

# === Функции ===

def create_menger_sponge(size, level):
    if level == 0:
        return [(0, 0, 0, size)]
    cubes = []
    new_size = size / 3
    for x in range(-1, 2):
        for y in range(-1, 2):
            for z in range(-1, 2):
                sum_abs = abs(x) + abs(y) + abs(z)
                if sum_abs > 1:
                    child_cubes = create_menger_sponge(new_size, level - 1)
                    for cx, cy, cz, csize in child_cubes:
                        cubes.append((x * new_size + cx, y * new_size + cy, z * new_size + cz, csize))
    return cubes

def generate_cube_vertices(x, y, z, size):
    half = size / 2
    return [
        (x - half, y - half, z - half),
        (x + half, y - half, z - half),
        (x + half, y + half, z - half),
        (x - half, y + half, z - half),
        (x - half, y - half, z + half),
        (x + half, y - half, z + half),
        (x + half, y + half, z + half),
        (x - half, y + half, z + half),
    ]

def generate_cube_indices(offset=0):
    return [
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (2, 3, 7, 6),
        (0, 3, 7, 4),
        (1, 2, 6, 5),
    ]

def generate_menger_sponge(size, level):
    cubes = create_menger_sponge(size, level)
    vertices = []
    indices = []
    offset = 0
    for x, y, z, cube_size in cubes:
        cube_vertices = generate_cube_vertices(x, y, z, cube_size)
        vertices.extend(cube_vertices)
        cube_indices = generate_cube_indices(offset)
        indices.extend([(a + offset, b + offset, c + offset, d + offset) for a, b, c, d in cube_indices])
        offset += len(cube_vertices)
    return np.array(vertices, dtype="f4"), np.array(indices, dtype="i4")

def init_context():
    return moderngl.create_standalone_context()

def render_frame(ctx, vertices, indices, rotation):
    vbo = ctx.buffer(vertices.tobytes())
    ibo = ctx.buffer(indices.tobytes())

    prog = ctx.program(
        vertex_shader="""
        #version 330
        in vec3 in_vert;
        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 proj;
        out vec3 frag_pos;

        void main() {
            frag_pos = (model * vec4(in_vert, 1.0)).xyz;
            gl_Position = proj * view * vec4(frag_pos, 1.0);
        }
        """,
        fragment_shader="""
        #version 330
        in vec3 frag_pos;
        out vec4 fragColor;

        uniform vec3 light_positions[6];
        uniform vec3 object_color;
        uniform vec3 ambient_color;
        uniform float transparency;
        uniform float light_intensity;

        void main() {
            vec3 normal = normalize(frag_pos);
            vec3 ambient = ambient_color * light_intensity;

            vec3 diffuse = vec3(0.0);
            for (int i = 0; i < 6; i++) {
                vec3 light_dir = normalize(light_positions[i] - frag_pos);
                float diff = max(dot(normal, light_dir), 0.0);
                diffuse += diff * object_color * light_intensity;
            }

            vec3 color = ambient + diffuse;
            fragColor = vec4(color, transparency);
        }
    """,
    )

    vao = ctx.vertex_array(prog, [(vbo, "3f", "in_vert")], ibo)

    model = np.eye(4, dtype="f4")
    cos_r = math.cos(rotation)
    sin_r = math.sin(rotation)
    axis = np.array(ROTATION_AXIS, dtype="f4")
    axis = axis / np.linalg.norm(axis)
    ux, uy, uz = axis
    model[:3, :3] = [
        [cos_r + ux ** 2 * (1 - cos_r), ux * uy * (1 - cos_r) - uz * sin_r, ux * uz * (1 - cos_r) + uy * sin_r],
        [uy * ux * (1 - cos_r) + uz * sin_r, cos_r + uy ** 2 * (1 - cos_r), uy * uz * (1 - cos_r) - ux * sin_r],
        [uz * ux * (1 - cos_r) - uy * sin_r, uz * uy * (1 - cos_r) + ux * sin_r, cos_r + uz ** 2 * (1 - cos_r)],
    ]

    view = np.eye(4, dtype="f4")
    view[3, 2] = -CAMERA_DISTANCE

    proj = np.eye(4, dtype="f4")
    proj[0, 0] = HEIGHT / WIDTH / math.tan(math.radians(45) / 2.0)
    proj[1, 1] = 1.0 / math.tan(math.radians(45) / 2.0)
    proj[2, 2] = -1001.0 / 999.0
    proj[2, 3] = -1.0
    proj[3, 2] = -2.0 * 1000.0 / 999.0
    proj[3, 3] = 0.0

    prog["model"].write(model.tobytes())
    prog["view"].write(view.tobytes())
    prog["proj"].write(proj.tobytes())
    prog["object_color"].write(np.array(OBJECT_COLOR, dtype="f4").tobytes())
    prog["ambient_color"].write(np.array(AMBIENT_COLOR, dtype="f4").tobytes())
    prog["transparency"].value = TRANSPARENCY
    prog["light_intensity"].value = LIGHT_INTENSITY
    prog["light_positions"].write(np.array(LIGHT_POSITIONS, dtype="f4").tobytes())  # Передаём массив источников света

    ctx.enable(moderngl.DEPTH_TEST)

    fbo = ctx.framebuffer(
        color_attachments=[ctx.texture((WIDTH, HEIGHT), 4)],
        depth_attachment=ctx.depth_texture((WIDTH, HEIGHT)),
    )
    fbo.use()
    ctx.clear(*BACKGROUND_COLOR, 1.0)
    vao.render()

    data = fbo.read(components=3)
    return Image.frombytes("RGB", (WIDTH, HEIGHT), data)


def save_frames_to_images():
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    ctx = init_context()
    vertices, indices = generate_menger_sponge(SPONGE_SIZE, SPONGE_LEVEL)
    for frame in range(FRAMES):
        print(f"Рендеринг кадра {frame + 1}/{FRAMES}...")
        rotation = frame * ROTATION_SPEED
        image = render_frame(ctx, vertices, indices, rotation)
        image.save(os.path.join(TEMP_DIR, f"frame_{frame:04d}.png"))

    print(f"Все кадры сохранены в папку {TEMP_DIR}")


def create_video_from_images(output_path=OUTPUT_FILE):
    images = sorted(
        [os.path.join(TEMP_DIR, img) for img in os.listdir(TEMP_DIR) if img.endswith(".png")]
    )
    with imageio.get_writer(output_path, fps=FPS, codec="libx264") as writer:
        for img_path in images:
            image = Image.open(img_path)
            writer.append_data(np.array(image))
    print(f"Видео сохранено в {output_path}")


def cleanup_temp_images():
    for img_file in os.listdir(TEMP_DIR):
        file_path = os.path.join(TEMP_DIR, img_file)
        if os.path.isfile(file_path):
            os.remove(file_path)
    os.rmdir(TEMP_DIR)
    print(f"Временная папка {TEMP_DIR} удалена.")


def render_video_with_temp_images():
    save_frames_to_images()
    create_video_from_images()
    cleanup_temp_images()


if __name__ == "__main__":
    render_video_with_temp_images()