#!/bin/bash
NODE_COUNT=$(kubectl get nodes --no-headers | wc -l | tr -d ' ')
echo -n "$NODE_COUNT" | xxd