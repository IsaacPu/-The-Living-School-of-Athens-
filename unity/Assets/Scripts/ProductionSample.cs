using System;
using System.IO;
using UnityEngine;

namespace AthensProduction
{
    [Serializable] public sealed class SceneParameters
    {
        public int schema_version;
        public string stage, reference_note;
        public int[] reference_crop_pixels, reference_original_pixels;
        public Vector3 hero_position, plato_position;
        public float hero_vertical_fov, hero_vanishing_y_top, platform_height, platform_front_z;
        public float hall_half_width, hall_back_z, front_vault_radius, front_vault_spring_y;
        public float front_vault_start_z, front_vault_end_z, middle_arch_z, middle_arch_radius, middle_arch_spring_y;
        public float far_arch_z, far_arch_radius, far_arch_spring_y, far_arch_x_scale, plato_yaw;
        public int coffer_angle_count, coffer_depth_count;
        public string[] notes;
    }

    public sealed class ProductionSample : MonoBehaviour
    {
        public Camera visitorCamera;
        public CharacterController visitor;
        public Transform character;
        public string characterSha256, characterStatus, characterAssetPath;
        public float characterBodyHeight;
        public SceneParameters parameters;
        public bool verifying, hideInterface;
        public string currentView = "hero";
        private float pitch, verticalVelocity;
        private bool roaming;
        private Font font;
        private string selected = "";

        private void Start()
        {
            Application.targetFrameRate = 60;
            font = Resources.Load<Font>("NotoSansSC");
            SetView("hero");
            Debug.Log("[AthensProduction] READY product=" + Application.productName + " character=" + characterStatus +
                      " sha256=" + characterSha256 + " body_height_m=" + characterBodyHeight + " backend=disabled");
            var args = Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length - 1; i++)
                if (args[i] == "--verify-production")
                {
                    verifying = true;
                    hideInterface = true;
                    var probe = gameObject.AddComponent<SampleVerification>();
                    probe.outputDirectory = Path.GetFullPath(args[i + 1]);
                    break;
                }
        }

        private void Update()
        {
            if (verifying) return;
            if (Input.GetKeyDown(KeyCode.Alpha1) || Input.GetKeyDown(KeyCode.R)) SetView("hero");
            if (Input.GetKeyDown(KeyCode.Alpha2)) SetView("close");
            if (Input.GetKeyDown(KeyCode.Alpha3)) SetView("side");
            if (Input.GetKeyDown(KeyCode.Alpha4)) SetView("return");
            if (Input.GetKeyDown(KeyCode.H)) hideInterface = !hideInterface;
            if (Input.GetKeyDown(KeyCode.Return)) BeginRoaming();
            if (Input.GetKeyDown(KeyCode.Escape)) { Cursor.lockState = CursorLockMode.None; Cursor.visible = true; }
            if (!roaming) return;
            if (Input.GetMouseButtonDown(1)) { Cursor.lockState = CursorLockMode.Locked; Cursor.visible = false; }
            if (Cursor.lockState == CursorLockMode.Locked)
            {
                visitor.transform.Rotate(0, Input.GetAxis("Mouse X") * 1.7f, 0);
                pitch = Mathf.Clamp(pitch - Input.GetAxis("Mouse Y") * 1.7f, -70, 70);
                visitorCamera.transform.localRotation = Quaternion.Euler(pitch, 0, 0);
            }
            var direction = visitor.transform.forward * Input.GetAxisRaw("Vertical") + visitor.transform.right * Input.GetAxisRaw("Horizontal");
            Drive(Vector3.ClampMagnitude(direction, 1) * 2.1f, Time.deltaTime);
            if (visitor.transform.position.y < -3) BeginRoaming();
            if (Input.GetMouseButtonDown(0))
            {
                var ray = Cursor.lockState == CursorLockMode.Locked ? visitorCamera.ViewportPointToRay(new Vector3(.5f, .5f, 0)) : visitorCamera.ScreenPointToRay(Input.mousePosition);
                selected = Physics.Raycast(ray, out var hit, 4f) && hit.collider.GetComponentInParent<CharacterMarker>() != null
                    ? "柏拉图 · 静态诊断母版；本阶段无问答服务" : "";
            }
        }

        public void Drive(Vector3 velocity, float dt)
        {
            verticalVelocity = visitor.isGrounded ? -2 : verticalVelocity + Physics.gravity.y * dt;
            visitor.Move((velocity + Vector3.up * verticalVelocity) * dt);
        }

        public void BeginRoaming()
        {
            visitor.enabled = false;
            visitor.transform.SetPositionAndRotation(new Vector3(0, .04f, -5), Quaternion.identity);
            visitorCamera.transform.localPosition = new Vector3(0, 1.65f, 0);
            visitorCamera.transform.localRotation = Quaternion.identity;
            visitor.enabled = true;
            visitorCamera.ResetProjectionMatrix();
            visitorCamera.ResetAspect();
            visitorCamera.fieldOfView = 57;
            pitch = 0; verticalVelocity = 0; roaming = true; currentView = "roaming";
            if (!verifying) { Cursor.lockState = CursorLockMode.Locked; Cursor.visible = false; }
            Physics.SyncTransforms();
        }

        public void SetView(string view)
        {
            roaming = false; visitor.enabled = false; currentView = view;
            visitor.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            visitorCamera.ResetProjectionMatrix();
            visitorCamera.transform.rotation = Quaternion.identity;
            if (view == "hero")
            {
                visitorCamera.transform.position = parameters.hero_position;
                visitorCamera.fieldOfView = parameters.hero_vertical_fov;
                SetHeroProjection(4f / 3f);
            }
            else
            {
                visitorCamera.fieldOfView = view == "close" ? 45 : 55;
                Vector3 target;
                if (view == "close") { visitorCamera.transform.position = new Vector3(-.7f, 1.85f, -1.85f); target = new Vector3(-.7f, 1.96f, 0); }
                else if (view == "side") { visitorCamera.transform.position = new Vector3(2.1f, 2.4f, 1.6f); target = new Vector3(-.7f, 1.8f, 0); }
                else { visitorCamera.transform.position = new Vector3(0, 2.45f, 8); target = new Vector3(0, 3.5f, -4); }
                visitorCamera.transform.LookAt(target);
            }
            Cursor.lockState = CursorLockMode.None; Cursor.visible = true;
        }

        public void SetHeroProjection(float aspect)
        {
            visitorCamera.aspect = aspect;
            var matrix = Matrix4x4.Perspective(parameters.hero_vertical_fov, aspect, visitorCamera.nearClipPlane, visitorCamera.farClipPlane);
            matrix[1, 2] = 2 * (parameters.hero_vanishing_y_top - .5f);
            visitorCamera.projectionMatrix = matrix;
        }

        private void OnGUI()
        {
            if (hideInterface) return;
            GUI.skin.font = font;
            GUI.skin.label.fontSize = 18;
            GUI.Box(new Rect(18, 18, 660, 116), "");
            GUI.Label(new Rect(32, 28, 630, 30), "雅典学院 · A-P0 结构 / 人物合模样板");
            GUI.Label(new Rect(32, 58, 630, 30), "Enter 漫游　WASD 移动　右键环视　Esc 释放鼠标");
            GUI.Label(new Rect(32, 88, 630, 30), "1 主视图　2 近景　3 侧视　4 回望　H 隐藏提示");
            GUI.Label(new Rect(26, Screen.height - 70, Screen.width - 52, 60), "静态人物诊断版 · 建筑结构样板，非完整精修 · 无后端 / 无实时 AI\n" + selected);
            if (GUI.Button(new Rect(Screen.width - 130, 24, 108, 34), "开始漫游")) BeginRoaming();
        }
    }

}
