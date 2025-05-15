// Import required modules
import * as THREE from './lib/three.module.js';
import { OrbitControls } from './lib/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from './lib/CSS2DRenderer.js';

/**
 * Class representing a 3D visualization of space debris and satellites.
 */
class SpaceDebrisVisualization {
    /**
     * Create a SpaceDebrisVisualization.
     */
    constructor() {
        console.log('SpaceDebrisVisualization constructor called');
        // Initialize properties
        this.initialized = false;
        this.objects = new Map();
        this._debugLogged = false;
        this.raycaster = new THREE.Raycaster();
        this.pointer = new THREE.Vector2();
        this.debrisGroups = [];

        // Bind methods to preserve context
        this.animate = this.animate.bind(this);
        this.onWindowResize = this.onWindowResize.bind(this);
        this.handleWebSocketMessage = this.handleWebSocketMessage.bind(this);
        this.onCanvasClick = this.onCanvasClick.bind(this);
        this.onCanvasMouseMove = this.onCanvasMouseMove.bind(this);

        // Start initialization when document is loaded
        if (document.readyState === 'loading') {
            console.log('Document loading, waiting for DOMContentLoaded...');
            document.addEventListener('DOMContentLoaded', () => {
                console.log('DOMContentLoaded fired, initializing...');
                this.init();
            });
        } else {
            console.log('Document already loaded, starting immediately...');
            this.init();
        }
    }

    async init() {
        try {
            console.log('Starting application initialization...');
            const canvas = document.getElementById('debris-canvas');
            console.log('Canvas dimensions:', {
                width: canvas.width,
                height: canvas.height,
                clientWidth: canvas.clientWidth,
                clientHeight: canvas.clientHeight,
                style: canvas.style.cssText
            });
            await this.initializeVisualization();
            this.initWebSocket();
            this.initialized = true;
            console.log('Application initialization complete');
        } catch (error) {
            console.error('Error during initialization:', error);
        }
    }

    initWebSocket() {
        try {
            this.ws = new WebSocket('ws://localhost:8765');

            this.ws.onopen = () => {
                console.log('WebSocket connection established');
            };

            this.ws.onmessage = (event) => {
                try {
                    this.handleWebSocketMessage(event);
                } catch (error) {
                    console.error('Error handling WebSocket message:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            this.ws.onclose = () => {
                console.log('WebSocket connection closed');
                // Attempt to reconnect after a delay
                setTimeout(() => this.initWebSocket(), 5000);
            };
        } catch (error) {
            console.error('Error initializing WebSocket:', error);
            // Attempt to reconnect after a delay
            setTimeout(() => this.initWebSocket(), 5000);
        }
    }

    handleWebSocketMessage(event) {
        try {
            const data = JSON.parse(event.data);
            if (Array.isArray(data)) {
                // Log first object as sample
                if (data.length > 0) {
                    console.log('Sample space object:', {
                        type: data[0].type,
                        subtype: data[0].subtype,
                        name: data[0].name
                    });
                }
                this.updateSpaceObjects(data);
            } else {
                console.error('Received non-array data:', data);
            }
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }

    async initializeVisualization() {
        console.log('Starting visualization initialization...');
        this.initializeScene();
        this.initializeCamera();
        this.initializeRenderer();
        this.initializeControls();
        this.initializeLights();
        await this.initializeTextureLoader();
        await this.loadTextures();
        this.setupEventListeners();
        console.log('Visualization initialization complete');
        requestAnimationFrame(this.animate);
    }

    initializeScene() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x000000);  // Black background

        // Add a subtle grid helper for reference
        const gridHelper = new THREE.GridHelper(50, 50, 0x444444, 0x222222);
        gridHelper.material.opacity = 0.3;
        gridHelper.material.transparent = true;
        this.scene.add(gridHelper);

        // Add axes helper
        const axesHelper = new THREE.AxesHelper(5);
        axesHelper.material.opacity = 0.5;
        axesHelper.material.transparent = true;
        this.scene.add(axesHelper);

        console.log('Scene initialized with black background');
        console.log('Scene children count:', this.scene.children.length);
        console.log('Scene:', {
            background: this.scene.background,
            fog: this.scene.fog,
            autoUpdate: this.scene.autoUpdate,
            helpers: ['grid', 'axes']
        });
    }

    initializeCamera() {
        const canvas = document.getElementById('debris-canvas');
        const aspect = canvas.clientWidth / canvas.clientHeight;
        this.camera = new THREE.PerspectiveCamera(
            75, // Field of view
            aspect,
            0.1,
            1000
        );
        this.camera.position.set(0, 5, 15);
        this.camera.lookAt(0, 0, 0);
        console.log('Camera initialized:', {
            position: this.camera.position,
            aspect: aspect,
            fov: this.camera.fov
        });
    }

    initializeRenderer() {
        const canvas = document.getElementById('debris-canvas');
        console.log('Canvas element:', canvas);
        console.log('Canvas dimensions:', {
            width: canvas.width,
            height: canvas.height,
            clientWidth: canvas.clientWidth,
            clientHeight: canvas.clientHeight,
            style: canvas.style.cssText
        });

        this.renderer = new THREE.WebGLRenderer({
            canvas: canvas,
            antialias: true,
            alpha: true
        });

        // Set size based on client dimensions
        this.renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.setClearColor(0x000000, 0); // Transparent background
        console.log('Renderer initialized with dimensions:', {
            width: this.renderer.domElement.width,
            height: this.renderer.domElement.height
        });
    }

    initLabelRenderer() {
        this.labelRenderer = new CSS2DRenderer();
        this.labelRenderer.setSize(window.innerWidth, window.innerHeight);
        this.labelRenderer.domElement.style.position = 'absolute';
        this.labelRenderer.domElement.style.top = '0';
        this.labelRenderer.domElement.style.left = '0';
        this.labelRenderer.domElement.style.pointerEvents = 'none';
        document.getElementById('visualization-container').appendChild(this.labelRenderer.domElement);
        console.log('Label renderer initialized');
    }

    initializeControls() {
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = false;
        this.controls.minDistance = 2;
        this.controls.maxDistance = 50;
        this.controls.maxPolarAngle = Math.PI;
        console.log('Controls initialized');
    }

    initializeLights() {
        const ambientLight = new THREE.AmbientLight(0x404040);
        this.scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight.position.set(5, 3, 5);
        this.scene.add(directionalLight);

        console.log('Lights initialized');
    }

    async initializeTextureLoader() {
        this.textureLoader = new THREE.TextureLoader();
        console.log('Texture loader initialized');
    }

    async loadTextures() {
        try {
            console.log('Starting texture load...');
            const [earthTexture, bumpMap] = await Promise.all([
                this.textureLoader.loadAsync('/static/textures/earth_texture.jpg'),
                this.textureLoader.loadAsync('/static/textures/earth_bumpmap.jpg')
            ]);

            await this.initializeEarth(earthTexture, bumpMap);
        } catch (error) {
            console.error('Error loading textures:', error);
        }
    }

    async initializeEarth(earthTexture, bumpMap) {
        console.log('Current scene children before Earth:', this.scene.children.length);
        const earthGeometry = new THREE.SphereGeometry(1, 32, 32);
        const earthMaterial = new THREE.MeshPhongMaterial({
            map: earthTexture,
            bumpMap: bumpMap,
            bumpScale: 0.05,
            specular: new THREE.Color(0x333333),
            shininess: 25
        });

        this.earth = new THREE.Mesh(earthGeometry, earthMaterial);
        this.scene.add(this.earth);
        console.log('Earth added to scene');
        console.log('Earth position:', this.earth.position);
        console.log('Earth scale:', this.earth.scale);
        console.log('Scene children after Earth:', this.scene.children.length);
        console.log('Earth initialized');
    }

    setupEventListeners() {
        window.addEventListener('resize', this.onWindowResize, false);
        this.renderer.domElement.addEventListener('click', this.onCanvasClick.bind(this));
        this.renderer.domElement.addEventListener('mousemove', this.onCanvasMouseMove.bind(this));
        console.log('Event listeners set up successfully');
    }

    onCanvasClick(event) {
        event.preventDefault();
        this.pointer.x = (event.clientX / window.innerWidth) * 2 - 1;
        this.pointer.y = -(event.clientY / window.innerHeight) * 2 + 1;
        this.raycaster.setFromCamera(this.pointer, this.camera);

        const intersects = this.raycaster.intersectObjects(this.scene.children, true);
        if (intersects.length > 0) {
            const object = intersects[0].object;
            if (object.callback) {
                object.callback();
            }
        }
    }

    onCanvasMouseMove(event) {
        event.preventDefault();
        this.pointer.x = (event.clientX / window.innerWidth) * 2 - 1;
        this.pointer.y = -(event.clientY / window.innerHeight) * 2 + 1;
    }

    showObjectInfo(data) {
        const infoPanel = document.getElementById('info-panel');
        const title = data.type === 'satellite' ? 'Satellite' : 'Debris';
        infoPanel.innerHTML = `
            <h3>${title} Information</h3>
            <p>ID: ${data.id}</p>
            <p>Type: ${data.subtype}</p>
            <p>Status: ${data.status}</p>
            ${data.type === 'satellite' ? `<p>Launch Date: ${data.launch_date}</p>` : ''}
            <p>Orbital Period: ${Math.round(data.period / 60)} minutes</p>
            ${this.formatOrbitalElements(data.orbital_elements)}
        `;
        infoPanel.style.display = 'block';
    }

    createInfoPanel() {
        const infoPanel = document.createElement('div');
        infoPanel.id = 'info-panel';
        infoPanel.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 15px;
            border-radius: 5px;
            font-family: Arial, sans-serif;
            min-width: 200px;
            display: none;
            z-index: 1000;
        `;
        document.body.appendChild(infoPanel);
        return infoPanel;
    }

    onWindowResize() {
        const width = window.innerWidth;
        const height = window.innerHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();

        this.renderer.setSize(width, height);
        if (this.labelRenderer) {
            this.labelRenderer.setSize(width, height);
        }
    }

    animate() {
        if (!this.initialized) {
            console.log('Animation started but not initialized yet');
            requestAnimationFrame(this.animate);
            return;
        }

        requestAnimationFrame(this.animate);

        try {
            // Update controls
            if (this.controls) {
                this.controls.update();
            }

            // Rotate Earth
            if (this.earth) {
                this.earth.rotation.y += 0.002;
            }

            // Update object positions
            if (this.debrisGroups && this.debrisGroups.length > 0) {
                const currentTime = Date.now();
                this.debrisGroups.forEach(group => {
                    if (!group || !group.children) return;
                    try {
                    
                    group.children.forEach(object => {
                        if (object.userData && object.userData.trajectory) {
                            const startTime = object.userData.startTime || Date.now();
                            const period = object.userData.period * 1000 || 10000;
                            const elapsed = (currentTime - startTime) % period;
                            const progress = elapsed / period;
                            
                            if (object.userData.trajectory.length > 0) {
                                const pointIndex = Math.floor(progress * object.userData.trajectory.length);
                                const position = object.userData.trajectory[pointIndex];
                                if (position) {
                                    object.position.set(position.x, position.y, position.z);
                                }
                            }
                        }
                    });
                    } catch (error) {
                        console.error('Error updating object positions:', error);
                    }
                });
            }

            // Log scene state periodically
            if (!this._sceneLogged && this.scene) {
                console.log('Scene state:', {
                    children: this.scene.children.length,
                    camera: this.camera.position.toArray(),
                    earth: this.earth ? 'present' : 'missing',
                    groups: this.debrisGroups ? this.debrisGroups.length : 0
                });
                this._sceneLogged = true;
            }

            // Render
            if (this.renderer && this.scene && this.camera) {
                this.renderer.render(this.scene, this.camera);
                if (this.labelRenderer) {
                    this.labelRenderer.render(this.scene, this.camera);
                }
            }
        } catch (error) {
            console.error('Error in animation loop:', error);
        }
    }

    initWebSocket() {
        try {
            this.ws = new WebSocket('ws://localhost:8765');

            this.ws.onopen = () => {
                console.log('WebSocket connection established');
            };

            this.ws.onmessage = (event) => {
                try {
                    this.handleWebSocketMessage(event);
                } catch (error) {
                    console.error('Error handling WebSocket message:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            this.ws.onclose = () => {
                console.log('WebSocket connection closed');
                // Attempt to reconnect after a delay
                setTimeout(() => this.initWebSocket(), 5000);
            };
        } catch (error) {
            console.error('Error initializing WebSocket:', error);
            // Attempt to reconnect after a delay
            setTimeout(() => this.initWebSocket(), 5000);
        }
    }

    createGlowTexture(color, intensity = 0.8) {
        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        const context = canvas.getContext('2d');

        // Create gradient
        const gradient = context.createRadialGradient(
            canvas.width / 2,
            canvas.height / 2,
            0,
            canvas.width / 2,
            canvas.height / 2,
            canvas.width / 2
        );

        // Convert hex color to RGB components
        const rgb = {
            r: (color >> 16) & 255,
            g: (color >> 8) & 255,
            b: color & 255
        };

        console.log('Creating glow texture:', {
            color: color.toString(16).padStart(6, '0'),
            rgb: rgb,
            intensity: intensity
        });

        // Add color stops with intensity
        gradient.addColorStop(0, `rgba(${rgb.r},${rgb.g},${rgb.b},${intensity})`);
        gradient.addColorStop(0.5, `rgba(${rgb.r},${rgb.g},${rgb.b},${intensity * 0.5})`);
        gradient.addColorStop(1, 'rgba(0,0,0,0)');

        // Draw gradient
        context.fillStyle = gradient;
        context.fillRect(0, 0, canvas.width, canvas.height);

        const texture = new THREE.CanvasTexture(canvas);
        texture.needsUpdate = true;

        return texture;
    }

    getObjectColor(type, subtype) {
        if (type === 'PAYLOAD' || type === 'satellite') {
            // Use bright, neon colors for satellites
            switch (subtype) {
                case 'communication':
                    return 0x00ff88;  // Bright green
                case 'navigation':
                    return 0x00ffff;  // Cyan
                case 'earth_observation':
                    return 0x0088ff;  // Blue
                case 'weather':
                    return 0xff00ff;  // Magenta
                case 'military':
                    return 0xffff00;  // Yellow
                default:
                    return 0x00ff88;  // Default satellite color
            }
        } else if (type === 'ROCKET_BODY') {
            return 0xff4400;  // Orange-red
        } else {  // debris and other types
            switch (subtype) {
                case 'rocket_body':
                    return 0xff4400;  // Orange-red
                case 'fragment':
                    return 0xff8800;  // Orange
                case 'defunct_satellite':
                    return 0xff0088;  // Pink
                default:
                    return 0xff4400;  // Default debris color
            }
        }
    }

    getGlowIntensity(type) {
        // Satellites glow much brighter than debris
        return type === 'PAYLOAD' || type === 'satellite' ? 0.15 : 0.1;
    }

    getGlowSize(type) {
        // Satellites have much larger glow than debris
        return type === 'PAYLOAD' || type === 'satellite' ? 4 : 2;
    }

    formatOrbitalElements(elements) {
        if (!elements) return '';
        try {
            return `
                <h4>Orbital Elements:</h4>
                <ul>
                    ${Object.entries(elements).map(([key, value]) => 
                        `<li>${key}: ${value.toFixed(2)}</li>`
                    ).join('')}
                </ul>
            `;
        } catch (error) {
            console.error('Error formatting orbital elements:', error);
            return '';
        }
    }

    updateSpaceObjects(objects) {
        try {
            if (!Array.isArray(objects)) {
                console.error('Expected array of objects, got:', typeof objects);
                return;
            }

            // Create a new group for this batch of objects
            const group = new THREE.Group();
            this.scene.add(group);
            this.debrisGroups.push(group);

            // Process each object
            objects.forEach(data => {
                try {
                    // Map TLE types to our internal types
                    const type = data.type === 'PAYLOAD' ? 'satellite' : 'debris';
                    const subtype = data.subtype || 'unknown';

                    // Create the object
                    const object = new THREE.Mesh(
                        new THREE.SphereGeometry(0.1, 32, 32),
                        new THREE.MeshPhongMaterial({
                            color: this.getObjectColor(type, subtype),
                            emissive: this.getObjectColor(type, subtype),
                            emissiveIntensity: 0.1,
                            shininess: 30
                        })
                    );

                    // Set initial position
                    if (data.position) {
                        object.position.set(
                            data.position.x || 0,
                            data.position.y || 0,
                            data.position.z || 0
                        );
                    }

                    // Store metadata
                    object.userData = {
                        type: type,
                        subtype: subtype,
                        name: data.name || 'Unknown Object',
                        trajectory: data.trajectory || [],
                        period: data.period || 10,  // Default 10-second period
                        startTime: Date.now()
                    };

                    // Add glow effect
                    const glowSize = this.getGlowSize(type);
                    const glowTexture = this.createGlowTexture(
                        this.getObjectColor(type, subtype),
                        this.getGlowIntensity(type)
                    );

                    const spriteMaterial = new THREE.SpriteMaterial({
                        map: glowTexture,
                        transparent: true,
                        blending: THREE.AdditiveBlending
                    });

                    const sprite = new THREE.Sprite(spriteMaterial);
                    sprite.scale.set(glowSize, glowSize, 1);
                    object.add(sprite);

                    // Create label
                    const label = document.createElement('div');
                    label.className = 'object-label';
                    label.textContent = object.userData.name;
                    label.style.color = '#ffffff';
                    label.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
                    label.style.padding = '2px 5px';
                    label.style.borderRadius = '3px';
                    label.style.visibility = 'hidden';

                    const labelObject = new CSS2DObject(label);
                    labelObject.position.set(0, 0.5, 0);
                    object.add(labelObject);

                    // Add to group
                    group.add(object);
                } catch (error) {
                    console.error('Error creating space object:', error);
                }
            });

            console.log(`Added ${objects.length} objects to scene`);
        } catch (error) {
            console.error('Error updating space objects:', error);
        }
    }
}

// Initialize the application when the DOM is ready
console.log('Script loaded, initializing application...');

// Create and initialize the visualization
function init() {
    console.log('Creating SpaceDebrisVisualization instance...');
    try {
        window.visualizer = new SpaceDebrisVisualization();
        console.log('SpaceDebrisVisualization created successfully');
    } catch (error) {
        console.error('Error creating SpaceDebrisVisualization:', error);
    }
}

if (document.readyState === 'loading') {
    console.log('Document loading, waiting for DOMContentLoaded...');
    document.addEventListener('DOMContentLoaded', init);
} else {
    console.log('Document already loaded, initializing immediately...');
    init();
}
