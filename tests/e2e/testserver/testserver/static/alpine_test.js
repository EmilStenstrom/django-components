document.addEventListener('alpine:init', () => {
    Alpine.data('alpine_test', () => ({
        somevalue: 123,
    }))
});
