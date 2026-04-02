/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{vue,js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: {
                    DEFAULT: '#002FA7', // 克莱因蓝
                    light: '#2E55C1',
                    dark: '#001D6E',
                },
                surface: {
                    DEFAULT: '#FFFFFF',
                    muted: '#FAFAFA',
                }
            },
            fontFamily: {
                sans: ['Inter', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
            },
            boxShadow: {
                'soft': '0 4px 20px -2px rgba(0, 0, 0, 0.05)',
                'float': '0 10px 30px -5px rgba(0, 47, 167, 0.08)',
            },
            borderRadius: {
                'xl': '12px',
                '2xl': '16px',
                '3xl': '24px',
            }
        },
    },
    plugins: [],
}
