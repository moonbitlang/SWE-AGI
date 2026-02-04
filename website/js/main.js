// Main JavaScript entry point for SWE-AGI website

document.addEventListener('DOMContentLoaded', function() {
    // Mobile navigation toggle
    const mobileNavToggle = document.querySelector('.mobile-nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    const navOverlay = document.querySelector('.nav-overlay');

    if (mobileNavToggle && navLinks) {
        mobileNavToggle.addEventListener('click', () => {
            navLinks.classList.toggle('mobile-open');
            navOverlay.classList.toggle('active');
        });

        if (navOverlay) {
            navOverlay.addEventListener('click', () => {
                navLinks.classList.remove('mobile-open');
                navOverlay.classList.remove('active');
            });
        }
    }
});

// Utility functions
function formatDuration(ms) {
    if (ms === null || ms === undefined) return 'N/A';
    const hours = ms / (1000 * 60 * 60);
    if (hours < 1) {
        return hours.toFixed(2) + 'h';
    }
    return hours.toFixed(1) + 'h';
}

function formatCost(cost) {
    if (cost === null || cost === undefined) return 'N/A';
    return '$' + cost.toFixed(2);
}

function formatTokens(tokens) {
    if (tokens === null || tokens === undefined) return 'N/A';
    if (tokens >= 1000000) {
        return (tokens / 1000000).toFixed(2) + 'M';
    }
    if (tokens >= 1000) {
        return (tokens / 1000).toFixed(1) + 'K';
    }
    return tokens.toString();
}
