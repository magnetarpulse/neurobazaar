<template>
  <div>
    <canvas id="myChart"></canvas>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { Chart } from 'chart.js/auto';

export default {
  name: 'ChartComponent',
  setup() {
    const chart = ref(null);

    onMounted(() => {
      const ctx = document.getElementById('myChart').getContext('2d');
      chart.value = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: ['January', 'February', 'March', 'April', 'May', 'June', 'July'],
          datasets: [{
            label: 'My First dataset',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 1,
            data: [65, 59, 80, 81, 56, 55, 40],
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true
            }
          }
        }
      });
    });

    return { chart };
  }
}
</script>

<style scoped>
canvas {
  max-width: 100%;
  height: 400px;
}
</style>
