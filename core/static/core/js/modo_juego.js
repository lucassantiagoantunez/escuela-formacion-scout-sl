(function () {
    let objetivoAlternativo = null;
    let botonActivo = null;

    function elementoFullscreen() {
        return document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement;
    }

    function estaInstalada() {
        return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
    }

    function esIphone() {
        return /iPhone|iPod/i.test(window.navigator.userAgent);
    }

    function actualizarBoton(boton, activo) {
        if (!boton) return;
        boton.textContent = activo ? 'Salir del modo juego' : 'Modo juego';
        boton.setAttribute('aria-pressed', activo ? 'true' : 'false');
    }

    function mostrarAvisoIphone() {
        if (!esIphone() || estaInstalada() || sessionStorage.getItem('edifos-aviso-iphone')) return;

        const aviso = document.createElement('aside');
        aviso.className = 'aviso-modo-juego';
        aviso.setAttribute('role', 'status');
        aviso.innerHTML = '<strong>Modo juego en iPhone</strong><p>Chrome no puede ocultar por completo sus barras. Para jugar sin ellas, abrí Compartir y elegí <b>Agregar a pantalla de inicio</b>. Mientras tanto, este modo usa todo el espacio disponible.</p><button type="button">Entendido</button>';
        aviso.querySelector('button').addEventListener('click', function () {
            sessionStorage.setItem('edifos-aviso-iphone', '1');
            aviso.remove();
        });
        document.body.appendChild(aviso);
    }

    function activarAlternativo(boton, objetivo) {
        if (objetivoAlternativo && objetivoAlternativo !== objetivo) {
            objetivoAlternativo.classList.remove('modo-juego-alternativo');
        }
        objetivoAlternativo = objetivo;
        botonActivo = boton;
        objetivo.classList.add('modo-juego-alternativo');
        document.body.classList.add('modo-juego-activo');
        actualizarBoton(boton, true);
        window.scrollTo(0, 0);
        mostrarAvisoIphone();
        window.dispatchEvent(new Event('resize'));
    }

    function desactivarAlternativo() {
        if (objetivoAlternativo) objetivoAlternativo.classList.remove('modo-juego-alternativo');
        document.body.classList.remove('modo-juego-activo');
        actualizarBoton(botonActivo, false);
        objetivoAlternativo = null;
        botonActivo = null;
        window.dispatchEvent(new Event('resize'));
    }

    async function alternar(boton, objetivo) {
        if (!objetivo) return;

        if (objetivo.classList.contains('modo-juego-alternativo')) {
            desactivarAlternativo();
            return;
        }

        if (elementoFullscreen()) {
            const salir = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen;
            if (salir) await salir.call(document);
            return;
        }

        const entrar = objetivo.requestFullscreen || objetivo.webkitRequestFullscreen || objetivo.msRequestFullscreen;
        if (entrar) {
            try {
                await entrar.call(objetivo);
                botonActivo = boton;
                actualizarBoton(boton, true);
                return;
            } catch (error) {
                // iPhone y algunos navegadores rechazan el Fullscreen API para elementos comunes.
            }
        }

        activarAlternativo(boton, objetivo);
    }

    function estaActivo(objetivo) {
        return Boolean(elementoFullscreen()) || Boolean(objetivo && objetivo.classList.contains('modo-juego-alternativo'));
    }

    ['fullscreenchange', 'webkitfullscreenchange', 'msfullscreenchange'].forEach(function (evento) {
        document.addEventListener(evento, function () {
            if (!elementoFullscreen() && !objetivoAlternativo) actualizarBoton(botonActivo, false);
            if (elementoFullscreen()) actualizarBoton(botonActivo, true);
        });
    });

    document.addEventListener('keydown', function (evento) {
        if (evento.key === 'Escape' && objetivoAlternativo) desactivarAlternativo();
    });

    window.EDIFOSModoJuego = { alternar: alternar, estaActivo: estaActivo };
})();
