using System;
using UnityEngine;

namespace AthensProduction
{
    public enum EntranceState { GalleryIdle, GalleryRoaming, Entering, AcademyRoaming, Returning }
    [Serializable] public sealed class EntrancePose
    {
        public Vector3 eye;
        public Quaternion rotation;
        public float fov, aspect, projectionShift;
        public Matrix4x4 projection;
    }

    public sealed class EntranceFlow : MonoBehaviour
    {
        public Renderer mural;
        public Material paintingBridgeTemplate;
        public Transform galleryRoot;
        public Vector3 galleryStartEye, galleryStartLookAt, triggerFeet, muralCenter;
        public float muralWidth, muralHeight, durationSeconds=7;
        public Rect studyRegionTop = new Rect(410f/3820,78f/2388,3072f/3820,2304f/2388);
        public EntranceState State {get;private set;}
        public EntrancePose LastAutomaticPose {get;private set;}
        public EntrancePose LastPreEntryPose {get;private set;}
        public float Progress {get;private set;}
        public float MuralAlpha {get;private set;}
        public float BridgeAlpha {get;private set;}
        public bool BridgeEnabled => bridgeRenderer!=null && bridgeRenderer.enabled;
        public int CompletedEntries {get;private set;}
        public int CompletedReturns {get;private set;}
        public int CancelledEntries {get;private set;}
        public bool IsAutomatic => State==EntranceState.Entering || State==EntranceState.Returning;
        public bool CanReturn => State==EntranceState.AcademyRoaming && Mathf.Abs(app.visitor.transform.position.x)<2 && app.visitor.transform.position.z>-7 && app.visitor.transform.position.z<-3;
        public bool CanEnter => State==EntranceState.GalleryRoaming && Mathf.Abs(app.visitor.transform.position.x)<1.8f && app.visitor.transform.position.z>-20.2f && app.visitor.transform.position.z<-18.8f && app.visitorCamera.transform.forward.z>.35f;
        private ProductionSample app;
        private Material muralInstance;
        private Material bridgeMaterial;
        private Mesh bridgeMesh;
        private Renderer bridgeRenderer;
        private EntrancePose alignment, hero, landing, returnStart;
        private bool cancelling;
        private Font font;

        public void Initialize(ProductionSample sample)
        {
            app=sample; font=Resources.Load<Font>("NotoSansSC");
            muralInstance=Application.isPlaying?mural.material:mural.sharedMaterial;
            var aspect=4f/3;
            var studyHeight=muralHeight*studyRegionTop.height;
            var distance=studyHeight/(2*Mathf.Tan(sample.parameters.hero_vertical_fov*Mathf.Deg2Rad/2));
            var center=new Vector3((studyRegionTop.center.x-.5f)*muralWidth,muralCenter.y+(.5f-studyRegionTop.center.y)*muralHeight,muralCenter.z);
            float shift=2*(sample.parameters.hero_vanishing_y_top-.5f);
            alignment=MakePose(new Vector3(center.x,center.y-shift*studyHeight/2,muralCenter.z-distance),Quaternion.identity,50,aspect,shift);
            hero=MakePose(sample.parameters.hero_position,Quaternion.identity,sample.parameters.hero_vertical_fov,aspect,shift);
            landing=MakePose(new Vector3(0,1.675f,-5),Quaternion.identity,57,aspect,0);
            if(Application.isPlaying)CreatePaintingBridge();
            app.HoldForCinematic();
            Apply(MakePose(galleryStartEye,Quaternion.LookRotation(galleryStartLookAt-galleryStartEye),57,aspect,0));
            State=EntranceState.GalleryIdle;Progress=0;SetAlpha(1);SetBridgeAlpha(0);
            if(Application.isPlaying)Debug.Log("[Entrance] INITIALIZED duration="+durationSeconds+" alignment_eye="+alignment.eye+" landing="+landing.eye);
        }

        public void StartGalleryRoaming()
        {
            if(State!=EntranceState.GalleryIdle)return;
            app.AdoptCurrentView("gallery");State=EntranceState.GalleryRoaming;
        }

        public bool RequestEnter()
        {
            if(!CanEnter)return false;
            LastPreEntryPose=ReadPose();Progress=0;cancelling=false;
            app.HoldForCinematic();State=EntranceState.Entering;
            Debug.Log("[Entrance] ENTER_BEGIN from="+LastPreEntryPose.eye);return true;
        }
        public bool RequestSkip()
        {
            if(State!=EntranceState.Entering)return false;
            Progress=1;ApplyEntry(1);FinishEntry("skip");return true;
        }
        public bool RequestCancel()
        {
            if(State!=EntranceState.Entering)return false;
            State=EntranceState.Returning;cancelling=true;
            Debug.Log("[Entrance] CANCEL_BEGIN progress="+Progress);return true;
        }
        public bool RequestReturn()
        {
            if(!CanReturn)return false;
            returnStart=ReadPose();Progress=0;cancelling=false;
            app.HoldForCinematic();State=EntranceState.Returning;
            Debug.Log("[Entrance] RETURN_BEGIN from="+returnStart.eye);return true;
        }

        public void HandleInput()
        {
            if(Input.GetKeyDown(KeyCode.H))app.hideInterface=!app.hideInterface;
            if(State==EntranceState.GalleryIdle)
            {
                if(Input.GetKeyDown(KeyCode.Return))StartGalleryRoaming();return;
            }
            if(State==EntranceState.Entering)
            {
                if(Input.GetKeyDown(KeyCode.Space))RequestSkip();
                else if(Input.GetKeyDown(KeyCode.Escape))RequestCancel();
                return;
            }
            if(State==EntranceState.Returning)return;
            if(State==EntranceState.GalleryRoaming && Input.GetKeyDown(KeyCode.E) && RequestEnter())return;
            if(State==EntranceState.AcademyRoaming && Input.GetKeyDown(KeyCode.R) && RequestReturn())return;
            app.ProcessRoamingInput();
            if(app.visitor.transform.position.y<-3)
            {
                if(State==EntranceState.AcademyRoaming)
                {
                    app.HoldForCinematic();Apply(landing);app.AdoptCurrentView("academy");
                    Debug.LogWarning("[Entrance] Recovered unsupported visitor to academy landing.");
                }
                else {app.HoldForCinematic();Apply(MakePose(galleryStartEye,Quaternion.LookRotation(galleryStartLookAt-galleryStartEye),57,4f/3,0));app.AdoptCurrentView("gallery");}
            }
        }

        private void Update()
        {
            if(app==null)return;
            if(State==EntranceState.Entering)
            {
                Progress=Mathf.Min(1,Progress+Time.unscaledDeltaTime/durationSeconds);
                ApplyEntry(Progress);if(Progress>=1)FinishEntry("normal");
            }
            else if(State==EntranceState.Returning)
            {
                if(cancelling)
                {
                    Progress=Mathf.Max(0,Progress-Time.unscaledDeltaTime/durationSeconds);
                    ApplyEntry(Progress);
                    if(Progress<=0){Apply(LastPreEntryPose);SetAlpha(1);app.AdoptCurrentView("gallery");State=EntranceState.GalleryRoaming;CancelledEntries++;Debug.Log("[Entrance] CANCEL_DONE");}
                }
                else
                {
                    Progress=Mathf.Min(1,Progress+Time.unscaledDeltaTime/6f);
                    var pose=Progress<.28f?Lerp(returnStart,hero,Progress/.28f):Progress<.50f?hero:Progress<.72f?Lerp(hero,alignment,(Progress-.50f)/.22f):Lerp(alignment,LastPreEntryPose,(Progress-.72f)/.28f);
                    Apply(pose);
                    SetAlpha(Progress>=.72f?1:0);
                    SetBridgeAlpha(Progress<.28f?0:Progress<.50f?Smooth(.28f,.50f,Progress):Progress<.72f?1:0);
                    if(Progress>=1){Apply(LastPreEntryPose);SetAlpha(1);SetBridgeAlpha(0);app.AdoptCurrentView("gallery");State=EntranceState.GalleryRoaming;CompletedReturns++;Debug.Log("[Entrance] RETURN_DONE");}
                }
            }
        }

        private void ApplyEntry(float t)
        {
            var pose=t<.30f?Lerp(LastPreEntryPose,alignment,t/.30f):t<.50f?Lerp(alignment,hero,(t-.30f)/.20f):t<.72f?hero:Lerp(hero,landing,(t-.72f)/.28f);
            Apply(pose);
            // The full-frame crop holds while the hidden camera travels. Only blend
            // the painting with 3D once the actual camera is stationary at P0 hero.
            SetAlpha(t<.30f?1:0);
            SetBridgeAlpha(t<.30f?0:t<.50f?1:1-Smooth(.50f,.72f,t));
        }
        private void FinishEntry(string reason)
        {
            Apply(landing);SetAlpha(0);SetBridgeAlpha(0);LastAutomaticPose=ReadPose();
            app.AdoptCurrentView("academy");State=EntranceState.AcademyRoaming;CompletedEntries++;
            Debug.Log("[Entrance] HANDOFF reason="+reason+" eye="+LastAutomaticPose.eye+" fov="+LastAutomaticPose.fov);
        }
        public EntrancePose ReadPose()
        {
            var c=app.visitorCamera;return new EntrancePose{eye=c.transform.position,rotation=c.transform.rotation,fov=c.fieldOfView,aspect=c.aspect,projectionShift=c.projectionMatrix[1,2],projection=c.projectionMatrix};
        }
        private void Apply(EntrancePose pose){app.SetCinematicPose(pose.eye,pose.rotation,pose.fov,pose.aspect,pose.projectionShift);}
        private static EntrancePose MakePose(Vector3 eye,Quaternion rotation,float fov,float aspect,float shift){return new EntrancePose{eye=eye,rotation=rotation,fov=fov,aspect=aspect,projectionShift=shift};}
        private static EntrancePose Lerp(EntrancePose a,EntrancePose b,float t)
        {
            t=Mathf.SmoothStep(0,1,Mathf.Clamp01(t));return MakePose(Vector3.Lerp(a.eye,b.eye,t),Quaternion.Slerp(a.rotation,b.rotation,t),Mathf.Lerp(a.fov,b.fov,t),Mathf.Lerp(a.aspect,b.aspect,t),Mathf.Lerp(a.projectionShift,b.projectionShift,t));
        }
        private static float Smooth(float a,float b,float t){return Mathf.SmoothStep(0,1,Mathf.InverseLerp(a,b,t));}
        private void SetAlpha(float value){MuralAlpha=value;muralInstance.SetColor("_BaseColor",new Color(1,1,1,value));mural.enabled=value>.0001f;}
        private void CreatePaintingBridge()
        {
            bridgeMaterial=new Material(paintingBridgeTemplate);
            var physicalScale=muralInstance.mainTextureScale;
            bridgeMaterial.mainTextureScale=Vector2.Scale(physicalScale,studyRegionTop.size);
            bridgeMaterial.mainTextureOffset=muralInstance.mainTextureOffset+Vector2.Scale(physicalScale,new Vector2(studyRegionTop.x,1-studyRegionTop.y-studyRegionTop.height));
            var screen=new GameObject("Painting crop bridge - camera space",typeof(MeshFilter),typeof(MeshRenderer));
            screen.transform.SetParent(app.visitorCamera.transform,false);
            bridgeMesh=new Mesh{name="Runtime camera-space painting quad"};
            bridgeMesh.vertices=new Vector3[4];
            bridgeMesh.uv=new[]{new Vector2(0,0),new Vector2(0,1),new Vector2(1,1),new Vector2(1,0)};
            bridgeMesh.triangles=new[]{0,1,2,0,2,3};
            screen.GetComponent<MeshFilter>().sharedMesh=bridgeMesh;
            bridgeRenderer=screen.GetComponent<MeshRenderer>();bridgeRenderer.sharedMaterial=bridgeMaterial;
            bridgeRenderer.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;
            bridgeRenderer.receiveShadows=false;
        }
        private void SetBridgeAlpha(float value)
        {
            BridgeAlpha=value;
            if(bridgeRenderer==null)return;
            bridgeRenderer.enabled=value>.0001f;
            bridgeMaterial.SetColor("_BaseColor",new Color(1,1,1,value));
            if(!bridgeRenderer.enabled)return;
            var camera=app.visitorCamera;
            var corners=new[]{new Vector3(0,0,.2f),new Vector3(0,1,.2f),new Vector3(1,1,.2f),new Vector3(1,0,.2f)};
            bridgeMesh.vertices=Array.ConvertAll(corners,point=>camera.transform.InverseTransformPoint(camera.ViewportToWorldPoint(point)));
            bridgeMesh.RecalculateBounds();
        }
        private void OnDestroy()
        {
            if(!Application.isPlaying)return;
            if(muralInstance!=null)Destroy(muralInstance);
            if(bridgeMaterial!=null)Destroy(bridgeMaterial);
            if(bridgeMesh!=null)Destroy(bridgeMesh);
        }
        private void OnGUI()
        {
            if(app==null||app.hideInterface)return;
            GUI.skin.font=font;GUI.skin.label.fontSize=18;
            GUI.Box(new Rect(18,18,690,110),"");
            string title=State==EntranceState.AcademyRoaming?"画中学院 · 一人结构样板":"签字厅 · 走进《雅典学院》";
            GUI.Label(new Rect(32,28,660,28),title);
            string hint=State==EntranceState.GalleryIdle?"Enter 开始展厅漫游 · 到中央圆纹后部面向壁画按 E":State==EntranceState.Entering?"镜头正在穿画 · Space 跳过 · Esc 取消":State==EntranceState.Returning?"正在返回展厅…":State==EntranceState.AcademyRoaming?(CanReturn?"WASD 漫游 · 右键环视 · R 返回展厅":"返回展厅：走回台阶前中央的金色地面标记，再按 R"):"WASD 到中央圆纹后部 · 右键面向壁画 · E 进入";
            GUI.Label(new Rect(32,59,660,28),hint);
            GUI.Label(new Rect(32,88,660,26),"场所关系研究灰盒 · 邻墙壁画与人物细节尚未完成");
            if(State==EntranceState.GalleryIdle&&GUI.Button(new Rect(Screen.width-170,24,145,36),"开始展厅漫游"))StartGalleryRoaming();
            if(CanEnter){GUI.Label(new Rect(Screen.width/2-130,Screen.height*.70f,300,35),"按 E，走进画中");if(GUI.Button(new Rect(Screen.width-170,24,145,36),"走进画中"))RequestEnter();}
            if(CanReturn&&GUI.Button(new Rect(Screen.width-170,24,145,36),"返回展厅"))RequestReturn();
        }
    }
}
