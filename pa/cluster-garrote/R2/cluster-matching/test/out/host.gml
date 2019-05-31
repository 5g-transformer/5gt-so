graph [
  node [
    id 0
    label "h2"
    cluster 2
    host_name "h2"
    capabilities [ 
      storage 1000
      cpu 16
      memory 128
    ]
  ]
  node [
    id 1
    label "h1"
    cluster 1
    host_name "h1"
    capabilities [ 
      storage 1000
      cpu 16
      memory 128
    ]
  ]
  edge [
    source 0
    target 1
    capacoty 1000
    delay 0.001
  ]
]
