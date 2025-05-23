import moderngl
import numpy as np
from PIL import Image
import imageio
import math

# === Базовые параметры ===
WIDTH = 1920          # Ширина кадра
HEIGHT = 1080         # Высота кадра
FRAMES = 240          # Количество кадров
FPS = 30              # Частота кадров
OUTPUT_FILE = "MengerSponge.mp4"  # Имя выходного файла

# === Параметры губки Менгера ===
SPONGE_SIZE = 2       # Размер губки Менгера
SPONGE_LEVEL = 4      # Уровень рекурсии губки Менгера

# === Параметры камеры ===
CAMERA_DISTANCE = 8   # Расстояние камеры от центра

# === Параметры освещения ===
LIGHT_POSITION = [-5, -5, -5]  # Положение источника света в пространстве (X, Y, Z).
# X - отвечает за смещение света влево/вправо (отрицательное значение - влево, положительное - вправо).
# Y - отвечает за смещение света вверх/вниз (отрицательное значение - вниз, положительное - вверх).
# Z - отвечает за смещение света ближе/дальше от объекта (отрицательное значение - ближе, положительное - дальше).

# === Параметры вращения ===
ROTATION_AXIS = [0, 1, 0]   # Ось вращения (например, [0, 1, 0] для вращения вокруг Y)
ROTATION_SPEED = 2 * math.pi / FRAMES  # Скорость вращения (угол на кадр)

# === Параметры цвета ===
OBJECT_COLOR = [0.5, 0.5, 1.0]  # Цвет объекта (RGB)
AMBIENT_COLOR = [0.1, 0.1, 0.2] # Цвет фонового освещения (RGB)
TRANSPARENCY = 1.0              # Прозрачность объекта (1.0 = непрозрачный)

# === Графические функции ===
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
        indices.extend([(a+offset, b+offset, c+offset, d+offset) for a, b, c, d in cube_indices])
        offset += len(cube_vertices)
    return np.array(vertices, dtype="f4"), np.array(indices, dtype="i4")

def init_context():
    ctx = moderngl.create_standalone_context()
    return ctx

def render_frame(ctx, vertices, indices, rotation, frame):
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

        uniform vec3 light_pos;
        uniform vec3 object_color;
        uniform vec3 ambient_color;
        uniform float transparency;

        void main() {
            // Нормаль (приблизительная)
            vec3 normal = normalize(frag_pos);
            // Направление света
            vec3 light_dir = normalize(light_pos - frag_pos);
            float diff = max(dot(normal, light_dir), 0.0);
            vec3 diffuse = diff * object_color;

            // Фоновое освещение
            vec3 ambient = ambient_color;

            // Финальный цвет
            vec3 color = ambient + diffuse;
            fragColor = vec4(color, transparency);
        }
        """,
    )

    vao = ctx.vertex_array(prog, [(vbo, "3f", "in_vert")], ibo)

    # Матрица модели (вращение)
    model = np.eye(4, dtype="f4")
    cos_r = math.cos(rotation)
    sin_r = math.sin(rotation)
    axis = np.array(ROTATION_AXIS, dtype="f4")
    axis = axis / np.linalg.norm(axis)  # Нормализация оси вращения
    ux, uy, uz = axis
    model[:3, :3] = [
        [cos_r + ux**2 * (1 - cos_r), ux * uy * (1 - cos_r) - uz * sin_r, ux * uz * (1 - cos_r) + uy * sin_r],
        [uy * ux * (1 - cos_r) + uz * sin_r, cos_r + uy**2 * (1 - cos_r), uy * uz * (1 - cos_r) - ux * sin_r],
        [uz * ux * (1 - cos_r) - uy * sin_r, uz * uy * (1 - cos_r) + ux * sin_r, cos_r + uz**2 * (1 - cos_r)],
    ]

    # Матрица вида (камера)
    view = np.eye(4, dtype="f4")
    view[3, 2] = -CAMERA_DISTANCE

    # Матрица проекции (перспективная)
    proj = np.eye(4, dtype="f4")
    proj[0, 0] = HEIGHT / WIDTH / math.tan(math.radians(45) / 2.0)
    proj[1, 1] = 1.0 / math.tan(math.radians(45) / 2.0)
    proj[2, 2] = -1001.0 / 999.0
    proj[2, 3] = -1.0
    proj[3, 2] = -2.0 * 1000.0 / 999.0
    proj[3, 3] = 0.0

    # Передача uniform-переменных
    prog["model"].write(model.tobytes())
    prog["view"].write(view.tobytes())
    prog["proj"].write(proj.tobytes())
    prog["light_pos"].write(np.array(LIGHT_POSITION, dtype="f4").tobytes())
    prog["object_color"].write(np.array(OBJECT_COLOR, dtype="f4").tobytes())
    prog["ambient_color"].write(np.array(AMBIENT_COLOR, dtype="f4").tobytes())
    prog["transparency"].value = TRANSPARENCY

    # Рендеринг
    fbo = ctx.framebuffer(color_attachments=[ctx.texture((WIDTH, HEIGHT), 4)])
    fbo.use()
    ctx.clear(0.0, 0.0, 0.0, 1.0)
    vao.render()

    data = fbo.read(components=3)
    image = Image.frombytes("RGB", (WIDTH, HEIGHT), data)
    return image

def render_video(output_path=OUTPUT_FILE):
    ctx = init_context()
    vertices, indices = generate_menger_sponge(SPONGE_SIZE, SPONGE_LEVEL)
    with imageio.get_writer(output_path, fps=FPS, codec="libx264") as writer:
        for frame in range(FRAMES):
            print(f"Рендеринг кадра {frame + 1}/{FRAMES}...")
            rotation = frame * ROTATION_SPEED
            image = render_frame(ctx, vertices, indices, rotation, frame)
            writer.append_data(np.array(image))

    print(f"Видео сохранено в {output_path}")

if __name__ == "__main__":
    render_video()