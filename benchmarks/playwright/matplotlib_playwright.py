from playwright.sync_api import sync_playwright
import numpy as np

def test_histogram_render_time():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        print("Going to the page")
        page.goto("https://localhost:8080?key=a2V5")
        print("Page loaded")

        print("Waiting for the figure to be visible")
        page.wait_for_selector(".mpld3-figure", timeout=5000)
        print("Figure is visible")

        render_times = []

        for i in range(103):  
            print(f"Benchmark {i} of 102")
            try:
                slider_thumb = page.locator(".v-slider__thumb-container") 
                slider_track = page.locator(".v-slider__track-container")  

                slider_track_box = slider_track.bounding_box()
                assert slider_track_box is not None

                percentage = i / 100
                new_position_x = slider_track_box["x"] + slider_track_box["width"] * percentage
                new_position_y = slider_track_box["y"] + slider_track_box["height"] / 2

                page.mouse.move(new_position_x, new_position_y)

                if i == 0:
                    page.mouse.down()
                elif i == 100:
                    page.mouse.up()

                result_handle = page.wait_for_function(
                    """
                    () => {
                        if (!window.__check_count) {
                            window.__check_count = 0;
                        }
                        if (!window.__stable_check_count) {
                            window.__stable_check_count = 0;
                        }
                        if (!window.__start_time) {
                            window.__start_time = performance.now();
                        }
                        if (!window.__stability_check_time) {
                            window.__stability_check_time = 0;
                        }
                        const STABLE_THRESHOLD = 10;  // Number of consecutive stable checks required

                        window.__check_count += 1;

                        const matplotlibFigure = document.querySelector('.mpld3-figure');
                        if (!matplotlibFigure) return false;

                        const previousState = window.__previous_matplotlib_state || null;
                        const currentState = {
                            innerHTML: matplotlibFigure.innerHTML,
                            attributes: Array.from(matplotlibFigure.attributes).reduce((acc, attr) => {
                                acc[attr.name] = attr.value;
                                return acc;
                            }, {})
                        };

                        // Measure stability check time
                        const stability_check_start = performance.now();

                        if (previousState && JSON.stringify(previousState) === JSON.stringify(currentState)) {
                            window.__stable_check_count += 1;
                        } else {
                            window.__stable_check_count = 0;
                        }

                        const stability_check_end = performance.now();
                        window.__stability_check_time += stability_check_end - stability_check_start;

                        window.__previous_matplotlib_state = currentState;

                        if (window.__stable_check_count >= STABLE_THRESHOLD) {
                            const end_time = performance.now();
                            
                            // Calculate both versions of render time
                            const total_render_time = end_time - window.__start_time;
                            const adjusted_render_time = total_render_time - window.__stability_check_time;

                            // Logging for verification 
                            const log = {
                                total_render_time,
                                stability_check_time: window.__stability_check_time,
                                adjusted_render_time,
                            };

                            console.log(log);

                            // Verify and choose the most appropriate render time
                            const final_render_time = 
                                adjusted_render_time > 0 ? adjusted_render_time : total_render_time;

                            // Reset variables
                            window.__check_count = 0;
                            window.__stable_check_count = 0;
                            window.__start_time = null;
                            window.__stability_check_time = 0;

                            return { final_render_time, log };
                        }

                        return false;
                    }
                    """,
                    timeout=60000,
                    polling=1
                )

                result = result_handle.json_value()
                final_render_time = result['final_render_time']
                log = result['log']
                render_times.append(final_render_time)
                print(f"Histogram render time: {final_render_time:.2f} milliseconds")
                print(f"Log: {log}")
            except Exception as e:
                print(f"Error in iteration {i}: {e}")

        browser.close()

        render_times.sort()
        min_val = np.min(render_times)
        q1 = np.percentile(render_times, 25)
        median = np.median(render_times)
        q3 = np.percentile(render_times, 75)
        max_val = np.max(render_times)
        mean = np.mean(render_times)
        std_dev = np.std(render_times)

        print("\nStatistics:")
        print(f"Minimum: {min_val:.2f} ms")
        print(f"First Quartile (Q1): {q1:.2f} ms")
        print(f"Median (Q2): {median:.2f} ms")
        print(f"Third Quartile (Q3): {q3:.2f} ms")
        print(f"Maximum: {max_val:.2f} ms")
        print(f"Mean: {mean:.2f} ms")
        print(f"Standard Deviation: {std_dev:.2f} ms")

if __name__ == "__main__":
    test_histogram_render_time()