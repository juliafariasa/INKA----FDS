
import * as THREE from 'three';
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';
import { MTLLoader } from 'three/addons/loaders/MTLLoader.js';

const root = document.getElementById('inka-director');

if (root) setupDirector(root);

async function setupDirector(root) {
  const el = id => root.querySelector('#' + id);

  const host = el('dc-webgl');
  const start = el('dc-start');
  const iris = el('dc-iris');
  const status = el('dc-status');
  const rec = el('dc-rec');
  const form = el('dc-form');
  const panel = el('dc-form-shell');
  const steps = [...root.querySelectorAll('.dc-step')];
  const track = [...root.querySelectorAll('[data-step-button]')];

  const prev = el('dc-prev');
  const next = el('dc-next');
  const submit = el('dc-submit');
  const shot = el('dc-shot');

  const fields = [
    el('titulo'),
    el('descricao'),
    el('url_video'),
    el('minutos')
  ];

  const motionOff = window.matchMedia(
    '(prefers-reduced-motion: reduce)'
  ).matches;

  const gsap = window.gsap;
  const errors = root.dataset.errors === '1';

  let renderer;
  let scene;
  let camera;
  let rig;
  let model;
  let room;
  let roomCamera;

  let lensWorld = new THREE.Vector3();
  let apertureRing;
  let lensLight;

  let reels = [];
  let focusRings = [];
  let crank = null;
  let lensFrames = [];

  let roomFrames = [];
  let filmRibbon = null;
  let roomLights = [];

  let loaded = false;
  let transitioning = false;
  let inRoom = false;

  let step = 0;
  let spin = 0;
  let spinGoal = 0;
  let lastTime = performance.now();

  let dragging = false;
  let pointerX = 0;
  let pointerY = 0;
  let dragX = 0;
  let dragY = 0;
  let dragTargetX = 0;
  let dragTargetY = 0;

  let roomPulse = 0;

  const pointerSupported = matchMedia(
    '(pointer:fine)'
  ).matches;

  // O formulário continua acessível sem WebGL.
  root.classList.add('dc-enhanced');

  if (errors) {
    const failed = root.querySelector(
      '#titulo[aria-invalid], #url_video[aria-invalid]'
    );

    showRoom(
      true,
      failed ? (failed.id === 'titulo' ? 0 : 2) : 3
    );
  }

  start.addEventListener('click', launch);

  prev.addEventListener(
    'click',
    () => setStep(step - 1)
  );

  next.addEventListener(
    'click',
    () => setStep(step + 1)
  );

  track.forEach((button, index) => {
    button.addEventListener(
      'click',
      () => setStep(index)
    );
  });

  for (const [i, field] of fields.entries()) {
    field.addEventListener('focus', () => {
      if (inRoom) setStep(i, true);
    });

    field.addEventListener('input', () => pulseRoom(i));
  }

  el('segundos').addEventListener(
    'input',
    () => pulseRoom(3)
  );

  el('segundos').addEventListener('focus', () => {
    if (inRoom) setStep(3, true);
  });

  form.addEventListener('submit', () => {
    if (inRoom) {
      root.classList.add('dc-is-saving');
      submit.textContent = 'ENVIANDO PRODUÇÃO...';
      spinGoal = 0;
    }
  });

  function showRoom(immediate = false, initialStep = 0) {
    if (inRoom && !immediate) return;

    inRoom = true;
    transitioning = false;

    root.classList.add('is-room');
    root.classList.remove('is-transitioning');

    start.setAttribute('aria-expanded', 'true');

    root.querySelector('.dc-room-title')
      .setAttribute('aria-hidden', 'false');

    setStep(initialStep);

    if (renderer) resize();

    if (!immediate) {
      setTimeout(() => {
        panel.scrollIntoView({
          behavior: motionOff ? 'auto' : 'smooth',
          block: 'start'
        });

        const title = panel.querySelector('h3');

        title.setAttribute('tabindex', '-1');
        title.focus({ preventScroll: true });
      }, 80);
    }
  }

  function setStep(value, fromFocus = false) {
    const nextStep = THREE.MathUtils.clamp(
      value, 0, 3
    );

    const changed = nextStep !== step;
    step = nextStep;

    steps.forEach((item, i) => {
      item.hidden = inRoom ? i !== step : false;
    });

    track.forEach((item, i) => {
      item.classList.toggle(
        'is-active', i === step
      );

      item.classList.toggle(
        'is-done', i < step
      );

      item.setAttribute(
        'aria-current',
        i === step ? 'step' : 'false'
      );
    });

    shot.textContent = `FRAME 0${step + 1} / 04`;

    prev.hidden = step === 0;
    next.hidden = step === 3;
    submit.hidden = step !== 3;

    if (inRoom && changed) advanceFilm();

    if (
      inRoom &&
      !fromFocus &&
      changed &&
      !motionOff
    ) {
      const input = steps[step].querySelector(
        'input,textarea'
      );

      input?.focus({ preventScroll: true });
    }
  }

  function pulseRoom(i) {
    if (
      !inRoom ||
      motionOff ||
      !gsap ||
      !roomFrames.length
    ) return;

    const frame = roomFrames[i];
    if (!frame) return;

    gsap.killTweensOf(frame.scale);

    gsap.fromTo(
      frame.scale,
      { x: 1, y: 1 },
      {
        x: 1.12,
        y: 1.12,
        duration: .18,
        repeat: 1,
        yoyo: true,
        ease: 'sine.inOut'
      }
    );

    const material = frame.userData.glow;

    gsap.fromTo(
      material,
      { opacity: .30 },
      {
        opacity: .85,
        duration: .16,
        repeat: 1,
        yoyo: true
      }
    );

    spinGoal = .45;
    roomPulse = 1;
  }

  function advanceFilm() {
    if (!filmRibbon) return;

    roomFrames.forEach((frame, i) => {
      frame.userData.glow.opacity =
        i === step ? .65 : .17;

      frame.userData.frame.material.opacity =
        i === step ? 1 : .35;
    });

    if (gsap && !motionOff) {
      gsap.to(filmRibbon.position, {
        x: (step - 1.5) * -1.85,
        duration: .8,
        ease: 'power3.inOut',
        overwrite: true
      });

      gsap.to(filmRibbon.rotation, {
        y: (step - 1.5) * .045,
        duration: .8,
        ease: 'power2.inOut',
        overwrite: true
      });
    } else {
      filmRibbon.position.x =
        (step - 1.5) * -1.85;
    }

    spinGoal = .35;
    roomPulse = .75;
  }

  function launch() {
    if (transitioning || inRoom) return;

    transitioning = true;
    root.classList.add('is-transitioning');

    start.disabled = true;
    rec.textContent = 'REC';
    status.textContent = 'ABRINDO A LENTE...';

    if (motionOff || !loaded || !gsap) {
      showRoom();
      return;
    }

    dragging = false;
    host.classList.remove('is-dragging');

    scene.updateMatrixWorld(true);

    const lensTarget = model.localToWorld(
      new THREE.Vector3(.345, .2165, 0)
    );

    // O eixo da lente deste OBJ aponta para +X.
    const lensAxis = new THREE.Vector3(1, 0, 0)
      .transformDirection(model.matrixWorld);

    const v = lensTarget.clone()
      .addScaledVector(lensAxis, .075);

    const tl = gsap.timeline({
      onComplete: () => {
        showRoom();

        gsap.to(iris, {
          opacity: 0,
          duration: .7,
          ease: 'power2.out',
          onComplete: () => {
            iris.style.clipPath =
              'circle(0% at 50% 46%)';
          }
        });
      }
    });

    const speed = { value: 0 };

    tl.to(speed, {
      value: 1,
      duration: .65,
      onUpdate: () => {
        spinGoal = speed.value * 2.5;
      }
    }, 0);

    // Movimento tridimensional da câmera.
    tl.to(rig.rotation, {
      y: -.38,
      x: .035,
      z: .04,
      duration: 1.15,
      ease: 'power2.inOut'
    }, 0);

    // Rotação dos anéis de foco.
    focusRings.forEach((ring, i) => {
      tl.to(ring.rotation, {
        x: ring.rotation.x + .42,
        duration: .8,
        ease: 'power2.inOut'
      }, .1 + i * .08);
    });

    // Movimento da manivela.
    if (crank) {
      tl.to(crank.rotation, {
        z: crank.rotation.z + Math.PI * .7,
        duration: .9,
        ease: 'power2.inOut'
      }, .05);
    }

    // Abertura luminosa da lente.
    if (apertureRing) {
      tl.to(apertureRing.scale, {
        x: 2.8,
        y: 2.8,
        z: 2.8,
        duration: .9,
        ease: 'power2.in'
      }, .65);

      tl.to(apertureRing.material, {
        opacity: .94,
        duration: .55
      }, .55);
    }

    if (lensLight) {
      tl.to(lensLight, {
        intensity: 8,
        duration: .85,
        ease: 'power2.in'
      }, .65);
    }

    // Quadros de película saindo da lente.
    lensFrames.forEach((f, i) => {
      tl.to(f.position, {
        x: f.position.x + .24 + i * .13,
        duration: .95,
        ease: 'power2.out'
      }, .7 + i * .13);

      tl.to(f.material, {
        opacity: .75,
        duration: .22,
        yoyo: true,
        repeat: 1
      }, .7 + i * .13);

      tl.to(f.scale, {
        x: 2.7 + i,
        y: 2.7 + i,
        duration: .9
      }, .7 + i * .13);
    });

    // Aproximação real da câmera virtual à lente.
    tl.to(camera.position, {
      x: v.x,
      y: v.y,
      z: v.z,
      duration: 1.75,
      ease: 'power3.inOut',
      onUpdate: () => {
        scene.updateMatrixWorld(true);

        const aim = model.localToWorld(
          new THREE.Vector3(.345, .2165, 0)
        );

        camera.lookAt(aim);
      }
    }, .4);

    tl.to(camera, {
      fov: 65,
      duration: 1.55,
      ease: 'power2.in',
      onUpdate: () => camera.updateProjectionMatrix()
    }, .4);

    // Íris da transição alinhada à lente projetada.
    tl.call(() => {
      scene.updateMatrixWorld(true);

      const projected = model.localToWorld(
        new THREE.Vector3(.345, .2165, 0)
      ).project(camera);

      const x = THREE.MathUtils.clamp(
        (projected.x * .5 + .5) * 100,
        8,
        92
      );

      const y = THREE.MathUtils.clamp(
        (-.5 * projected.y + .5) * 100,
        8,
        92
      );

      iris.style.setProperty('--iris-x', `${x}%`);
      iris.style.setProperty('--iris-y', `${y}%`);

      iris.style.clipPath =
        `circle(0% at ${x}% ${y}%)`;
    }, null, 1.68);

    tl.to(iris, {
      opacity: 1,
      duration: .04
    }, 1.73);

    tl.to(iris, {
      clipPath: () => `circle(115% at ${iris.style.getPropertyValue('--iris-x')} ${iris.style.getPropertyValue('--iris-y')})`,
      duration: .65,
      ease: 'power3.in'
    }, 1.73);

    tl.call(() => {
      status.textContent =
        'ENTRANDO NA SALA DE PROJEÇÃO';
    }, null, 1.42);
  }

  // Pivô 3D para girar as peças reais.
  function createPivot(parts, worldPoint) {
    if (!parts.length) return null;

    model.updateMatrixWorld(true);

    const pivot = new THREE.Group();

    pivot.position.copy(
      model.worldToLocal(worldPoint.clone())
    );

    model.add(pivot);
    model.updateMatrixWorld(true);

    parts.forEach(part => pivot.attach(part));

    return pivot;
  }

  function buildMovingParts() {
    const meshes = [];

    model.traverse(o => {
      if (o.isMesh) meshes.push(o);
    });

    const mesh = name =>
      meshes.find(o => o.name === name);

    const center = obj =>
      new THREE.Box3()
        .setFromObject(obj)
        .getCenter(new THREE.Vector3());

    for (const side of ['left', 'right']) {
      const base = mesh(`reel_${side}_drum`);
      if (!base) continue;

      const parts = meshes.filter(o =>
        o.name.startsWith(`reel_${side}_`)
      );

      const pivot = createPivot(parts, center(base));

      if (pivot) reels.push(pivot);
    }

    for (let i = 0; i < 3; i++) {
      const part = mesh(`focus_ring_${i}`);

      if (part) {
        focusRings.push(
          createPivot([part], center(part))
        );
      }
    }

    const hub = mesh('crank_hub');

    if (hub) {
      crank = createPivot(
        meshes.filter(o =>
          [
            'crank_hub',
            'crank_shaft',
            'crank_grip'
          ].includes(o.name)
        ),
        center(hub)
      );
    }
  }

  function makeLensEffects() {
    const mat = new THREE.MeshBasicMaterial({
      color: 0xb9d188,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0,
      depthWrite: false,
      blending: THREE.AdditiveBlending
    });

    const local = new THREE.Vector3(
      .345, .2165, 0
    );

    model.updateMatrixWorld(true);

    lensWorld.copy(
      model.localToWorld(local.clone())
    );

    apertureRing = new THREE.Mesh(
      new THREE.RingGeometry(.032, .037, 64),
      mat
    );

    apertureRing.rotation.y = Math.PI / 2;
    apertureRing.position.copy(local);

    model.add(apertureRing);

    lensLight = new THREE.PointLight(
      0xb9d188,
      0,
      1.35,
      2
    );

    lensLight.position.copy(local);
    model.add(lensLight);

    const edge = new THREE.EdgesGeometry(
      new THREE.PlaneGeometry(.14, .095)
    );

    for (let i = 0; i < 3; i++) {
      const frame = new THREE.LineSegments(
        edge,
        new THREE.LineBasicMaterial({
          color: 0xb9d188,
          transparent: true,
          opacity: 0,
          depthWrite: false
        })
      );

      frame.position.copy(local);
      frame.rotation.y = Math.PI / 2;
      frame.position.x += .025 + i * .015;

      model.add(frame);
      lensFrames.push(frame);
    }
  }

  function makeRoom() {
    room = new THREE.Scene();

    roomCamera = new THREE.PerspectiveCamera(
      38, 1, .05, 100
    );

    roomCamera.position.set(0, 0, 7.4);
    roomCamera.lookAt(0, 0, 0);

    room.add(
      new THREE.AmbientLight(0x608563, 1)
    );

    const key = new THREE.PointLight(
      0xb9d188, 4.5, 16, 2
    );

    key.position.set(-1, 2, 3);
    room.add(key);
    roomLights.push(key);

    const rim = new THREE.PointLight(
      0x5f7b44, 4, 16, 2
    );

    rim.position.set(3, -1, 1);
    room.add(rim);

    // Molduras em profundidade criam a sala de projeção.
    const gateGeo = new THREE.EdgesGeometry(
      new THREE.PlaneGeometry(8, 5)
    );

    for (let i = 0; i < 6; i++) {
      const gate = new THREE.LineSegments(
        gateGeo,
        new THREE.LineBasicMaterial({
          color: 0x6b9265,
          transparent: true,
          opacity: .22 - i * .025
        })
      );

      gate.position.z = -i * 2.5 - 1.5;
      gate.scale.setScalar(1 + i * .35);

      room.add(gate);
    }

    filmRibbon = new THREE.Group();
    room.add(filmRibbon);

    const perforationGeo = new THREE.BoxGeometry(
      .15, .12, .025
    );

    const perforationMat = new THREE.MeshStandardMaterial({
      color: 0x95b884,
      metalness: .4,
      roughness: .5
    });

    // Perfurações físicas da película.
    for (const side of [-1, 1]) {
      for (let i = 0; i < 22; i++) {
        const hole = new THREE.Mesh(
          perforationGeo,
          perforationMat
        );

        hole.position.set(
          (i - 10.5) * .39,
          side * 1.75,
          -2.1
        );

        filmRibbon.add(hole);
      }
    }

    const filmEdge = new THREE.EdgesGeometry(
      new THREE.PlaneGeometry(1.55, 2.85)
    );

    for (let i = 0; i < 4; i++) {
      const group = new THREE.Group();

      group.position.set(
        (i - 1.5) * 1.85,
        0,
        -2.25
      );

      const border = new THREE.LineSegments(
        filmEdge,
        new THREE.LineBasicMaterial({
          color: 0xb9d188,
          transparent: true,
          opacity: .38
        })
      );

      group.add(border);

      const filmPlane = new THREE.Mesh(
        new THREE.PlaneGeometry(1.43, 2.72),
        new THREE.MeshBasicMaterial({
          color: 0x2c4931,
          transparent: true,
          opacity: .19,
          side: THREE.DoubleSide,
          depthWrite: false
        })
      );

      group.add(filmPlane);

      const glowing = new THREE.Mesh(
        new THREE.PlaneGeometry(1.43, 2.72),
        new THREE.MeshBasicMaterial({
          color: 0xb9d188,
          transparent: true,
          opacity: .17,
          side: THREE.DoubleSide,
          depthWrite: false
        })
      );

      glowing.position.z = -.015;
      group.add(glowing);

      filmRibbon.add(group);

      group.userData.frame = border;
      group.userData.glow = glowing.material;
      roomFrames.push(group);
    }

    // Poeira suspensa no espaço tridimensional.
    const particles = Array.from(
      { length: 140 },
      () => [
        (Math.random() - .5) * 15,
        (Math.random() - .5) * 10,
        -Math.random() * 13
      ]
    );

    const geometry = new THREE.BufferGeometry();

    geometry.setAttribute(
      'position',
      new THREE.Float32BufferAttribute(
        particles.flat(),
        3
      )
    );

    const dust = new THREE.Points(
      geometry,
      new THREE.PointsMaterial({
        color: 0xb9d188,
        size: .018,
        transparent: true,
        opacity: .40,
        depthWrite: false
      })
    );

    room.add(dust);

    advanceFilm();
  }

  function resize() {
    if (!renderer) return;

    const width = Math.max(1, host.clientWidth);
    const height = Math.max(1, host.clientHeight);

    renderer.setSize(width, height, false);

    for (const cam of [camera, roomCamera]) {
      cam.aspect = width / height;
      cam.updateProjectionMatrix();
    }

    if (!model || transitioning) return;

    const size = new THREE.Box3()
      .setFromObject(rig)
      .getSize(new THREE.Vector3());

    const v = Math.tan(
      THREE.MathUtils.degToRad(camera.fov) / 2
    );

    const mobile = width < 700;

    const targetHeight = mobile ? .31 : .33;
    const targetWidth = mobile ? .65 : .35;

    const dH = size.y / (
      2 * v * targetHeight
    );

    const dW = size.length() * .7 / (
      2 * v * camera.aspect * targetWidth
    );

    const distance = Math.max(
      dH, dW, 1.2
    );

    const viewDirection = new THREE.Vector3(
      .85, .25, 1.7
    ).normalize();

    const target = new THREE.Vector3(
      0, -.08, 0
    );

    camera.position.copy(target)
      .addScaledVector(viewDirection, distance);

    camera.lookAt(target);
  }

  // Usuário arrasta para explorar o modelo 3D.
  function onPointerDown(e) {
    if (
      inRoom ||
      transitioning ||
      !loaded ||
      motionOff ||
      !pointerSupported
    ) return;

    dragging = true;

    pointerX = e.clientX;
    pointerY = e.clientY;

    dragX = dragTargetX;
    dragY = dragTargetY;

    host.classList.add('is-dragging');
    host.setPointerCapture?.(e.pointerId);
  }

  function onPointerMove(e) {
    if (!dragging) return;

    dragTargetX = THREE.MathUtils.clamp(
      dragX + (e.clientX - pointerX) * .006,
      -.7,
      .7
    );

    dragTargetY = THREE.MathUtils.clamp(
      dragY + (e.clientY - pointerY) * .004,
      -.25,
      .25
    );
  }

  function onPointerUp(e) {
    dragging = false;

    host.classList.remove('is-dragging');

    try {
      host.releasePointerCapture?.(e.pointerId);
    } catch {}
  }

  host.addEventListener(
    'pointerdown', onPointerDown
  );

  host.addEventListener(
    'pointermove', onPointerMove
  );

  host.addEventListener(
    'pointerup', onPointerUp
  );

  host.addEventListener(
    'pointercancel', onPointerUp
  );

  // Loop de renderização 3D.
  function tick(now) {
    requestAnimationFrame(tick);

    if (document.hidden || !renderer) {
      lastTime = now;
      return;
    }

    const dt = Math.min(
      .05,
      (now - lastTime) / 1000 || 0
    );

    lastTime = now;

    if (
      !transitioning &&
      rig &&
      !inRoom &&
      !motionOff
    ) {
      rig.rotation.y += (
        dragTargetX - rig.rotation.y
      ) * Math.min(1, dt * 4);

      rig.rotation.x += (
        dragTargetY - rig.rotation.x
      ) * Math.min(1, dt * 4);

      rig.position.y =
        Math.sin(now * .0007) * .008;
    }

    spin += (
      spinGoal - spin
    ) * Math.min(1, dt * 3);

    if (inRoom) {
      spinGoal += (
        0 - spinGoal
      ) * Math.min(1, dt * 3);

      roomPulse = Math.max(
        0,
        roomPulse - dt * 1.5
      );

      roomCamera.position.x =
        Math.sin(now * .00022) * .12;

      roomCamera.position.z =
        7.4 - roomPulse * .24;

      roomCamera.lookAt(0, 0, -2.7);

      if (filmRibbon && !motionOff) {
        filmRibbon.rotation.x =
          Math.sin(now * .00048) * .014;

        filmRibbon.position.y =
          Math.sin(now * .00033) * .025;
      }

      renderer.render(room, roomCamera);
    } else {
      reels.forEach(reel => {
        reel.rotation.z -= dt * spin * 2.3;
      });

      renderer.render(scene, camera);
    }
  }

  function loadError(err) {
    console.error(
      '[INKA DIRECTOR] Falha ao carregar o 3D:',
      err
    );

    status.textContent =
      'MODO SEM 3D · CADASTRO DISPONÍVEL';

    loaded = false;
  }

  try {
    const test = document.createElement('canvas');

    if (
      !test.getContext('webgl2') &&
      !test.getContext('webgl')
    ) {
      throw new Error('WebGL indisponível');
    }

    scene = new THREE.Scene();

    camera = new THREE.PerspectiveCamera(
      35,
      1,
      .015,
      100
    );

    renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance'
    });

    renderer.setPixelRatio(
      Math.min(
        window.devicePixelRatio || 1,
        1.75
      )
    );

    renderer.outputColorSpace =
      THREE.SRGBColorSpace;

    renderer.toneMapping =
      THREE.ACESFilmicToneMapping;

    renderer.toneMappingExposure = 1.25;

    host.appendChild(renderer.domElement);

    // Iluminação verde INKA.
    scene.add(
      new THREE.HemisphereLight(
        0xb9d188,
        0x0a170e,
        2.2
      )
    );

    const key = new THREE.DirectionalLight(
      0xf3f7e9,
      3.2
    );

    key.position.set(2, 3, 4);
    scene.add(key);

    const rim = new THREE.DirectionalLight(
      0xb9d188,
      4
    );

    rim.position.set(-3, 2, -1);
    scene.add(rim);

    const fill = new THREE.PointLight(
      0x5f7b44,
      5,
      5
    );

    fill.position.set(-1, -.4, 1);
    scene.add(fill);

    // Materiais e geometria da câmera real.
    const mtl = await new MTLLoader().loadAsync(
      root.dataset.mtl
    );

    mtl.preload();

    const loader = new OBJLoader();
    loader.setMaterials(mtl);

    model = await loader.loadAsync(
      root.dataset.obj
    );

    model.traverse(o => {
      if (!o.isMesh) return;

      const mats = Array.isArray(o.material)
        ? o.material
        : [o.material];

      mats.forEach(mat => {
        if (!mat) return;

        if (mat.color) {
          const isMetal = /silver|steel/.test(
            mat.name.toLowerCase()
          );

          mat.color.lerp(
            new THREE.Color(
              isMetal ? 0x9eb39d : 0x223427
            ),
            isMetal ? .3 : .22
          );
        }

        mat.shininess = /matte/.test(
          mat.name.toLowerCase()
        ) ? 20 : 100;

        mat.needsUpdate = true;
      });
    });

    // Centraliza o modelo.
    const bounds = new THREE.Box3()
      .setFromObject(model);

    const center = bounds.getCenter(
      new THREE.Vector3()
    );

    rig = new THREE.Group();

    model.position.sub(center);
    rig.add(model);

    scene.add(rig);
    scene.updateMatrixWorld(true);

    buildMovingParts();
    makeLensEffects();

    model.localToWorld(
      lensWorld.set(.345, .2165, 0)
    );

    makeRoom();

    loaded = true;

    if (!inRoom) {
      status.textContent =
        'EQUIPAMENTO PRONTO · ARRASTE PARA EXPLORAR';
    }

    resize();

    new ResizeObserver(resize).observe(host);

    requestAnimationFrame(tick);
  } catch (err) {
    loadError(err);
  }
}
